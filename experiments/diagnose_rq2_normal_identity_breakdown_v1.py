"""Bounded zero-solver H25 breakdown of validation, dependencies and encoding."""
from argparse import ArgumentParser
from copy import deepcopy
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
from src.rq2_joint_deliverability_boundary_v1 import normal_task_inputs_stream as preparation

from src.rq2_joint_deliverability_boundary_v1 import normal_execution_stream_fast as kernel
from src.rq2_joint_deliverability_boundary_v1 import normal_execution_stream as baseline
from src.rq2_joint_deliverability_boundary_v1 import identity_stream_fast as fast

c = prior.c
SCHEMA = 'rq2_normal_identity_breakdown_probe_v1'
COMPONENTS = ('deepcopy_seconds', 'input_identity_seconds', 'fast_input_identity_seconds',
    'validation_seconds', 'dependencies_seconds', 'encoding_digest_seconds', 'execution_identity_seconds',
    'model_build_seconds', 'model_scale_seconds', 'model_structure_seconds',
    'initial_snapshot_seconds', 'post_fast_input_identity_seconds', 'post_input_identity_seconds')
write, read = prior.write, prior.read


def implementation_identity():
    return source.stream.digest(SCHEMA, source.implementation_identity(),
        preparation.stream_binding.implementation_identity(),
        sha256(Path(preparation.__file__).read_bytes()).hexdigest(),
        tuple((Path(m.__file__).name, sha256(Path(m.__file__).read_bytes()).hexdigest())
            for m in (prior, prior.audit, kernel, kernel.streaming, kernel.native, kernel.legacy, fast, baseline)),
        sha256(Path(__file__).read_bytes()).hexdigest())


def assemble(request, expected_implementation):
    """Run full pinned streaming preparation, never a model or solver."""
    if source.implementation_identity() != expected_implementation:
        raise ValueError('source implementation drift')
    if c.worker.inputs.task_source_identity(request.source) != request.expected_source_request_identity:
        raise ValueError('legacy source declaration drift')
    return preparation.prepare_task_inputs(request.source,
        expected_request_identity=preparation.task_source_identity(request.source))


def component_costs(prepared, request):
    """Sequential component observations, not a normal execution or certificate."""
    timings = []
    def measure(name, operation):
        start = perf_counter()
        result = operation()
        timings.append([name, perf_counter()-start])
        return result
    owned = measure('deepcopy_seconds', lambda: deepcopy(prepared.assembly.inputs))
    before = measure('input_identity_seconds', lambda: baseline.normal_input_identity(owned))
    if before != request.source.expected_input_identity:
        raise ValueError('cost probe input identity mismatch')
    fast_before = measure('fast_input_identity_seconds', lambda: fast.normal_input_identity(owned))
    if fast_before != before:
        raise ValueError('fast input identity mismatch')
    measure('validation_seconds', lambda: fast.legacy._validate(owned))
    dependencies = measure('dependencies_seconds', fast.legacy._dependencies)
    decomposed = measure('encoding_digest_seconds', lambda: fast.digest(fast.legacy.CONTRACT, owned, dependencies))
    if decomposed != before:
        raise ValueError('decomposed input identity mismatch')
    execution = measure('execution_identity_seconds', lambda: kernel.normal_execution_identity(before,
        request.source.expected_scale, request.specification, request.execution_budget))
    model_pin = kernel.streaming.implementation_identity()
    model = measure('model_build_seconds', lambda: kernel.streaming.build_continuous_normal_model(owned,
        expected_identity=before, expected_implementation_identity=model_pin))
    scale = measure('model_scale_seconds', lambda: kernel.model_scale(model))
    if scale != request.source.expected_scale:
        raise ValueError('cost probe actual model scale mismatch')
    structure = measure('model_structure_seconds', lambda: kernel.native._structure(model))
    snapshot = measure('initial_snapshot_seconds', lambda: kernel.native._snapshot(model))
    fast_after = measure('post_fast_input_identity_seconds', lambda: fast.normal_input_identity(owned))
    after = measure('post_input_identity_seconds', lambda: baseline.normal_input_identity(owned))
    if before != after or fast_after != after or kernel.streaming.implementation_identity() != model_pin:
        raise ValueError('cost probe input or model implementation drift')
    return dict(component_timings=timings, model_builds=1, model_scale=asdict(scale),
        fast_encoder_sha256=sha256(Path(fast.__file__).read_bytes()).hexdigest(),
        fast_input_identity=fast_before, post_fast_input_identity=fast_after,
        decomposed_input_identity=decomposed,
        model_implementation_identity=model_pin, normal_execution_identity=execution,
        model_structure_identity=structure, initial_snapshot_variables=len(snapshot),
        initial_snapshot_identity=source.stream.digest(snapshot),
        component_costs_are_kernel_total=False, numerical_execution_performed=False)


def child(root, request, pin, stream_pin):
    def forbidden(*args, **kwargs): raise AssertionError('solver forbidden in source probe')
    kernel.native.create_solver = forbidden
    kernel.run_normal_only = forbidden
    c.worker.kernel.native.create_solver = forbidden
    c.worker.kernel.run_normal_only = forbidden
    c.worker.journal.execution.run_source_normal = forbidden
    started = perf_counter()
    try:
        write(root/'started.json', dict(schema=SCHEMA, pid=os.getpid(), formal_result=False))
        prepared = assemble(request, stream_pin)
        if type(prepared) is not preparation.PreparedStreamingNormalTaskInputs:
            raise ValueError('typed streaming preparation required')
        costs = component_costs(prepared, request)
        result = prepared.assembly
        if implementation_identity() != pin: raise ValueError('probe implementation drift')
        write(root/'costs.json', dict(schema=SCHEMA, pid=os.getpid(), **costs,
            prepared_request_identity=prepared.request_identity,
            binding_identity=prepared.binding.binding_identity,
            binding_implementation_identity=prepared.binding.implementation_identity,
            legacy_content_binding_identity=prepared.binding.legacy_content_binding_identity,
            legacy_binding_sha256=sha256(prepared.binding.legacy_content_json.encode()).hexdigest(),
            preparation_timings=dict(prepared.timings),
            normal_identity=result.normal_identity,
            legacy_content_assembly_identity=result.legacy_content_assembly_identity,
            assembly_identity=result.assembly_identity, implementation_identity=result.implementation_identity,
            probe_implementation_identity=pin, source_manifest_sha256=result.source_manifest_sha256,
            raw_source_hours=list(result.raw_source_hours), source_hours=list(result.inputs.source_hours),
            annual_source_hours=len(result.inputs.data.hourly_points),
            elapsed_seconds=perf_counter()-started,
            lifetime_peak_working_set_bytes=c.worker.kernel._peak_working_set_bytes(),
            solver_calls=prepared.solver_calls, mechanism_initial_state=prepared.mechanism_initial_state,
            observed_power_mapping=prepared.observed_power_mapping,
            normal_assignment_verified=prepared.normal_assignment_verified,
            formal_result=prepared.formal_result, whole_task_resources_verified=False))
    except BaseException as error:
        try:
            failure = prior.failure_record(error, 'normal_component_costs')
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
    if type(record['binding']) is not dict:
        raise ValueError('legacy binding object required')
    binding_body = dict(record['binding'])
    legacy_binding_pin = binding_body.pop('binding_identity')
    if (legacy_binding_pin != spec.expected_binding_identity
            or preparation.source.source_window._hash(binding_body) != legacy_binding_pin):
        raise ValueError('legacy binding external content mismatch')
    binding_wire = preparation.source._json(record['binding'])
    binding_impl = preparation.stream_binding.implementation_identity()
    binding_pin = source.stream.digest(preparation.stream_binding.CONTRACT, spec.expected_input_identity,
        assembly_pin, spec.expected_pair_identity, binding_wire, binding_impl)
    expected = dict(schema=SCHEMA, pid=pid,
        fast_encoder_sha256=sha256(Path(fast.__file__).read_bytes()).hexdigest(),
        fast_input_identity=spec.expected_input_identity, post_fast_input_identity=spec.expected_input_identity,
        decomposed_input_identity=spec.expected_input_identity,
        component_timings=content.get('component_timings'), model_builds=1,
        model_scale=asdict(spec.expected_scale), initial_snapshot_variables=spec.expected_scale.variables,
        model_implementation_identity=kernel.streaming.implementation_identity(),
        normal_execution_identity=kernel.normal_execution_identity(spec.expected_input_identity,
            spec.expected_scale, request.specification, request.execution_budget),
        model_structure_identity=content.get('model_structure_identity'),
        initial_snapshot_identity=content.get('initial_snapshot_identity'),
        component_costs_are_kernel_total=False, numerical_execution_performed=False, normal_identity=spec.expected_input_identity,
        prepared_request_identity=preparation.task_source_identity(spec),
        binding_identity=binding_pin, binding_implementation_identity=binding_impl,
        legacy_content_binding_identity=spec.expected_binding_identity,
        legacy_binding_sha256=sha256(binding_wire.encode()).hexdigest(),
        preparation_timings=content.get('preparation_timings'),
        legacy_content_assembly_identity=spec.expected_assembly_identity, assembly_identity=assembly_pin,
        implementation_identity=stream_pin, probe_implementation_identity=pin,
        source_manifest_sha256=power['grid_source_manifest_sha256'], raw_source_hours=hours,
        source_hours=[h+1 for h in hours], annual_source_hours=8784,
        elapsed_seconds=content.get('elapsed_seconds'),
        lifetime_peak_working_set_bytes=content.get('lifetime_peak_working_set_bytes'),
        solver_calls=0, mechanism_initial_state=True, observed_power_mapping=False,
        normal_assignment_verified=False,
        formal_result=False, whole_task_resources_verified=False)
    if (c.journal._bytes(content) != c.journal._bytes(expected)
            or type(content['elapsed_seconds']) is not float or not math.isfinite(content['elapsed_seconds'])
            or content['elapsed_seconds'] < 0
            or type(content['lifetime_peak_working_set_bytes']) is not int
            or content['lifetime_peak_working_set_bytes'] <= 0):
        raise ValueError('preparation diagnostic content mismatch')
    timings = content['preparation_timings']
    if (type(timings) is not dict or set(timings) != set(prior.TIMINGS)
            or any(type(value) is not float or not math.isfinite(value) or value < 0 for value in timings.values())
            or abs(timings['observed_total_seconds']-sum(timings[name] for name in prior.TIMINGS[:-1])) > 1e-6
            or timings['observed_total_seconds'] > content['elapsed_seconds']):
        raise ValueError('preparation timing mismatch')

    rows = content['component_timings']
    if (type(rows) is not list or len(rows) != len(COMPONENTS)
            or any(type(row) is not list or len(row) != 2 for row in rows)
            or tuple(row[0] for row in rows) != COMPONENTS
            or any(type(row[1]) is not float or not math.isfinite(row[1]) or row[1] < 0 for row in rows)
            or sum(row[1] for row in rows)+timings['observed_total_seconds'] > content['elapsed_seconds']+1e-6):
        raise ValueError('component timing inventory or elapsed projection mismatch')
    for name in ('model_structure_identity', 'initial_snapshot_identity'):
        kernel._pin(content[name])


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
                    or failure['stage'] != 'normal_component_costs' or failure['formal_result'] is not False
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
        if implementation_identity() != implementation:
            raise ValueError('post-quiescence probe implementation drift')
        content = read(root/'costs.json')
        validate_content(content, request, implementation, stream_pin, launch['pid'])
        if implementation_identity() != implementation:
            raise ValueError('post-validation probe implementation drift')
        if failure is not None or (root/'failure_write_failed.json').exists():
            raise ValueError('source failure present')
    except Exception as error:
        errors.append(type(error).__name__)
    return dict(schema=SCHEMA, status='unresolved_probe' if errors else 'normal_identity_breakdown_observed',
        observation_sha256=observation_digest,
        costs_sha256=sha256(c.journal._bytes(content)).hexdigest() if content is not None else None,
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
    prepared_pin = preparation.task_source_identity(request.source)
    if args.child:
        packet, launch = read(root/'request.json'), read(root/'launch.json')
        expected_host = c._host(root, budget, phase.max_job_commit_bytes, budget.scratch_bytes_per_phase)
        expected_process = c.process.task_process_identity(list(sys.orig_argv), cwd=root,
            environment=dict(environment, TEMP=str(root), TMP=str(root)), budget=phase, host_budget=expected_host,
            expected_host_identity=c.resources.resource_identity(expected_host))
        expected_packet = dict(schema=SCHEMA, argv=list(sys.orig_argv), environment=dict(os.environ),
            implementation_identity=args.expected_implementation, stream_implementation_identity=stream_pin,
            prepared_request_identity=prepared_pin,
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
            prepared_request_identity=prepared_pin,
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
