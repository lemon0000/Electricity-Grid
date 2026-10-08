"""Single-hour H1 calibration Job candidate; production execution stays closed.

The private seams are for bounded pre-seal tests. A completed development Job
does not grant numerical, source, resource, or formal experiment authority.
"""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
from math import isfinite
import os
from pathlib import Path
import sys

from . import normal_h1_full_collector_v3 as collector
from . import normal_h1_source_binding as source
from . import declared_task_process as process
from . import normal_h1_shape_process as files
from . import normal_h1_calibration_gate_v3 as gates
from . import normal_licensed_environment as licensed_environment
from ..solvers.rq2_solver_adapter import Rq2SolverSpec

SCHEMA = 'h1_full_single_hour_job_candidate_v3'
ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / 'experiments/run_rq2_normal_h1_full_job_worker_v3.py'
LIMIT = 256 * 1024


def implementation_identity():
    return source.h1._digest(SCHEMA, collector.implementation_identity(), source.implementation_identity(),
        tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest())
              for m in (process, process.legacy, process.legacy.process, files, gates,
                        licensed_environment, licensed_environment.legacy)),
        sha256(WORKER.read_bytes()).hexdigest(), sha256(Path(__file__).read_bytes()).hexdigest())


def bind_job(work, resource, serial_budget, limits, job_budget):
    """Pure declaration check; no files, observation, lease, or native call."""
    plan = collector.resources.check_plan((work,), (resource,), serial_budget)
    if not plan['declaration_consistent'] or work.hours != 1:
        raise ValueError('consistent complete single-hour inventory required')
    if type(limits) is not collector.base.replay.H1HourReplayLimits:
        raise ValueError('exact full-hour replay limits required')
    limits.__post_init__()
    if (limits.max_stages != len(work.stage_order)
            or limits.max_variables > resource.envelope.max_variables
            or limits.max_constraints > resource.envelope.max_constraints):
        raise ValueError('replay limits exceed or differ from task inventory')
    if type(job_budget) is not process.DeclaredTaskProcessBudget:
        raise ValueError('exact declared Job budget required')
    job_budget.__post_init__()
    if (job_budget.resource_contract_identity != plan['declaration_identity']
            or job_budget.envelope != resource.envelope
            or job_budget.max_job_commit_bytes != resource.envelope.max_job_commit_bytes
            or job_budget.max_elapsed_seconds + job_budget.max_quiescence_seconds != resource.envelope.max_wall_seconds
            or job_budget.max_elapsed_seconds < plan['tasks'][0]['required_declared_wall_seconds'] - job_budget.max_quiescence_seconds):
        raise ValueError('Job must bind the complete exact resource envelope')
    return plan


def _read(path, pin=None):
    path = process.legacy.resources.local._path(path)
    before = process.legacy.resources.local._file_identity(path)
    with path.open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if (len(raw) > LIMIT or process.legacy.resources.local._file_identity(path) != before
            or (pin is not None and sha256(raw).hexdigest() != pin)):
        raise ValueError('bounded stable pinned Job record required')
    return collector.base.replay.old._decode(raw, LIMIT), sha256(raw).hexdigest()


def _write(path, value):
    if len(source._bytes(value)) > LIMIT:
        raise ValueError('bounded Job record required')
    return files._write(path, value)


def _configuration(request):
    """Decode only explicit JSON dataclasses, never executable object payloads."""
    w = request['work']
    spec = Rq2SolverSpec(**w['specification'])
    work = collector.resources.H1NormalWork(w['task_id'], w['hours'],
        tuple(tuple(row) for row in w['stage_order']), spec)
    r = request['resource']
    envelope = collector.resources.serial.TaskEnvelope(**r['envelope'])
    resource = collector.resources.H1TaskResources(envelope, r['archive_overhead_bytes'])
    serial = collector.resources.serial.SerialResourceBudget(**request['serial_budget'])
    limits = collector.base.replay.H1HourReplayLimits(**request['limits'])
    j = dict(request['job_budget'])
    j['envelope'] = collector.resources.serial.TaskEnvelope(**j['envelope'])
    job = process.DeclaredTaskProcessBudget(**j)
    plan = bind_job(work, resource, serial, limits, job)
    return work, resource, serial, limits, job, plan


def _packet(request):
    declaration = source.H1SourceDeclaration(**request['source_declaration'])
    value = source.load_pinned_current(declaration, request['upstream_root'], config_path=request['config_path'])
    packet = source.assemble_pinned_current(value, request['upstream_root'],
        expected_identity=request['source_identity'], relative_hour=0, dc_bus=request['dc_bus'],
        config_path=request['config_path'])
    if packet.network.identity != request['network_identity']:
        raise ValueError('independent network pin mismatch')
    return packet


def _summary(inspection, anchor_pin):
    if type(inspection) is not collector.H1FullCollectorInspection:
        raise ValueError('exact full collector inspection required')
    if (inspection.whole_task_resources_verified is not False
            or inspection.formal_execution_ready is not False):
        raise ValueError('unexpected outer collector authority')
    item = inspection.inspection
    if type(item) is not collector.base.H1CollectorInspection:
        raise ValueError('exact inner inspection required')
    if any(getattr(item, field) is not False for field in ('resumable', 'source_authenticated',
            'native_execution_authenticated', 'parent_intent_verified', 'published', 'formal_result', 'formal_execution_ready')):
        raise ValueError('unexpected collector authority')
    return dict(status=item.status, registry_head=item.registry_head, child_head=item.child_head,
        stored_reports=item.stored_reports, solver_calls=item.solver_calls,
        projection_identity=None if item.projection is None else item.projection.projection_identity,
        anchor_record_sha256=anchor_pin, collector_identity=inspection.full_collector_identity,
        resource_declaration_identity=inspection.resource_declaration_identity)


REQUEST_FIELDS = set(('schema implementation_identity work resource serial_budget limits job_budget '
    'source_declaration source_identity network_identity upstream_root config_path dc_bus root').split())


def _validate_request(request):
    if (type(request) is not dict or set(request) != REQUEST_FIELDS or request['schema'] != SCHEMA
            or request['implementation_identity'] != implementation_identity()):
        raise ValueError('exact full Job request/implementation required')
    source.H1SourceDeclaration(**request['source_declaration'])
    for name in ('source_identity', 'network_identity'):
        source.windows._sha(request[name])
    if type(request['dc_bus']) is not int:
        raise ValueError('integer DC bus required')
    return _configuration(request)


def _execute_development_worker(request_path, request_pin, *, _gate=None):
    """Shared worker core; no native effects without a consumed exact gate."""
    sealed = gates.verify_consumed(_gate)
    source.windows._sha(request_pin)
    request, _ = _read(request_path, request_pin)
    if source._bytes(request) != source._bytes(sealed):
        raise ValueError('worker request differs from consumed gate')
    work, resource, serial, limits, job, plan = _validate_request(request)
    root = process.legacy.resources.local._path(request['root'])
    if (Path(request_path).resolve() != root / 'request.json'
            or Path.cwd().resolve() != root / 'scratch_non_authoritative'):
        raise ValueError('worker location differs from bound request')
    intent, _ = _read(root / 'intent.json')
    if intent != dict(schema=SCHEMA, request_sha256=request_pin, implementation_identity=request['implementation_identity'],
                      resource_declaration_identity=plan['declaration_identity'], formal_result=False):
        raise ValueError('durable controller intent required')
    packet = _packet(request)
    args = (root / 'collector_non_authoritative', packet, work, resource, serial, limits)
    kwargs = dict(anchor_root=root / 'anchor_non_authoritative', parent_intent_head=request_pin,
                  source_lineage_identity=request['source_identity'])
    owner = collector.DevelopmentH1FullCollector(*args, **kwargs, create=True)
    try:
        result = owner._run_development(expected_head=owner.inspect().inspection.registry_head, _gate=_gate)
        pin = owner._anchor.inspect().record_sha256
        summary = _summary(result, pin)
    finally:
        owner.close()
    # Independent owner and retained terminal pin; no reuse of an in-memory cache.
    with collector.base.replay.guard.solver_calls_forbidden():
        reopened = collector.DevelopmentH1FullCollector(*args, **kwargs, expected_anchor_record=pin)
        try:
            if _summary(reopened.inspect(), pin) != summary:
                raise ValueError('fresh terminal anchor/replay mismatch')
        finally:
            reopened.close()
        if _packet(request) != packet:
            raise ValueError('current source drift after collector')
    if implementation_identity() != request['implementation_identity']:
        raise ValueError('full Job implementation drift after replay')
    gates.verify_consumed(_gate)
    report = dict(schema=SCHEMA, request_sha256=request_pin, summary=summary,
        fresh_reopen_equal=True, solver_calls_by_replay=0, whole_task_resources_verified=False,
        formal_execution_ready=False, formal_result=False, native_execution_authenticated=False)
    _write(root / 'worker_result.json', report)
    return report


def run_job(root, request, *, gate=None):
    if gate is None:
        raise ValueError('sealed calibration package and independent review required before execution')
    _, sealed = gates.verify_gate(gate)
    if source._bytes(request) != source._bytes(sealed) or str(Path(root).resolve()) != sealed['root']:
        raise ValueError('execution differs from sealed single-hour request')
    gates.consume(gate)
    return _run_development_job(root, request, _gate=gate)


def _execute_calibration_worker(request_path, request_pin, gate_path, gate_pin):
    gate, _ = _read(gate_path, gate_pin)
    sealed = gates.verify_consumed(gate)
    if (sha256(source._bytes(sealed)).hexdigest() != request_pin
            or Path(gate_path).resolve() != Path(sealed['root'])/'calibration_gate.json'):
        raise ValueError('worker differs from consumed calibration request')
    result = _execute_development_worker(request_path, request_pin, _gate=gate)
    gates.verify_consumed(gate)
    return result


def _run_development_job(root, request, *, _gate=None):
    """Shared supervisor; every route requires the already consumed exact gate."""
    if source._bytes(gates.verify_consumed(_gate)) != source._bytes(request):
        raise ValueError('supervisor request differs from consumed gate')
    request = deepcopy(request)
    work, resource, serial, limits, job, plan = _validate_request(request)
    local = process.legacy.resources
    path = Path(root).resolve()
    if str(path) != request['root'] or not path.name.endswith('_non_authoritative'):
        raise ValueError('exclusive declared non-authoritative root required')
    lease = local.local._Lease(path, True)
    try:
        scratch = path / 'scratch_non_authoritative'
        scratch.mkdir()
        request_pin = _write(path / 'request.json', request)
        intent_pin = _write(path / 'intent.json', dict(schema=SCHEMA, request_sha256=request_pin,
            implementation_identity=request['implementation_identity'],
            resource_declaration_identity=plan['declaration_identity'], formal_result=False))
        host = local.HostResourceBudget(job.max_job_commit_bytes + serial.supervisor_additional_commit_bytes,
            serial.commit_reserve_bytes, (
                local.DirectoryDemand('archive', str(path), resource.envelope.archive_bytes, serial.disk_reserve_bytes),
                local.DirectoryDemand('scratch', str(scratch), resource.envelope.scratch_bytes, serial.disk_reserve_bytes)))
        env = licensed_environment.development_environment()
        env.update(TEMP=str(scratch), TMP=str(scratch))
        licensed_environment._environment(env)
        argv = [sys.executable, '-I', '-B', str(WORKER), str(path / 'request.json'), request_pin]
        if _gate is not None:
            if source._bytes(gates.verify_consumed(_gate)) != source._bytes(request):
                raise ValueError('consumed request drift before launch')
            gate_path = path/'calibration_gate.json'
            gate_pin = _write(gate_path, _gate)
            argv.extend((str(gate_path), gate_pin))
        args = dict(cwd=scratch, environment=env, budget=job, host_budget=host,
                    expected_host_identity=local.resource_identity(host))
        identity = process.task_process_identity(argv, **args)
        launch_pin = _write(path / 'launch_intent.json', dict(process_identity=identity, request_sha256=request_pin,
            host_budget=asdict(host), job_budget=asdict(job)))
        with process.declared_task_child(argv, **args, expected_process_identity=identity) as child:
            launched_pid, launched_creation = child.pid, child.creation_filetime
            child_pin = _write(path / 'child_identity.json', dict(pid=child.pid, creation_filetime=child.creation_filetime,
                process_identity=identity, initial_headroom=asdict(child.initial_observation)))
            lease.check()
            if implementation_identity() != request['implementation_identity']:
                raise ValueError('full Job implementation drift before release')
            child.release()
            observation = child.wait()
        if type(observation) is not process.legacy.TaskProcessObservation:
            _write(path/'observation_failure.json', dict(schema=SCHEMA, reason='unexpected_observation_type',
                process_identity=identity, pid=launched_pid, creation_filetime=launched_creation))
            raise ValueError('exact Job observation required')
        observation_pin = _write(path / 'process_observation.json', asdict(observation))
        if (observation.process_identity != identity or observation.pid != launched_pid
                or observation.creation_filetime != launched_creation
                or type(observation.pid) is not int or type(observation.creation_filetime) is not int):
            raise ValueError('Job observation differs from launched process')
        if (type(observation.last_resource_errors) is not tuple
                or type(observation.runtime_samples) is not int or observation.runtime_samples < 0
                or type(observation.elapsed_seconds) not in (int, float)
                or not isfinite(observation.elapsed_seconds) or observation.elapsed_seconds < 0
                or type(observation.job_peak_process_commit_bytes) is not int
                or type(observation.job_peak_total_commit_bytes) is not int):
            raise ValueError('invalid Job observation resource types')
        if (observation.reason != 'child_exited' or type(observation.exit_code) is not int
                or observation.exit_code != 0 or observation.whole_job_quiescent is not True
                or observation.job_commit_limits_configured is not True or observation.last_resource_errors
                or observation.observation_error_type is not None):
            raise ValueError('full Job unresolved; retained attempt cannot be retried')
        if any(getattr(observation, field) is not False for field in ('hard_disk_quota_enforced',
                'whole_task_resources_verified', 'numerical_evidence_verified', 'formal_result')):
            raise ValueError('unexpected Job observation authority')
        if (not 0 < observation.job_peak_process_commit_bytes <= job.max_process_commit_bytes
                or not 0 < observation.job_peak_total_commit_bytes <= job.max_job_commit_bytes):
            raise ValueError('Job commit observation exceeds bound')
        lease.check()
        if implementation_identity() != request['implementation_identity']:
            raise ValueError('full Job implementation drift after quiescence')
        retained = dict(request=request_pin, intent=intent_pin, launch_intent=launch_pin,
                        child_identity=child_pin, process_observation=observation_pin)
        for name, expected in retained.items():
            _read(path/(name+'.json'), expected)
        report, pin = _read(path / 'worker_result.json')
        _validate_report(report, request_pin, plan)
        if _gate is not None:
            gates.verify_consumed(_gate)
        _write(path / 'job_checks.json', dict(schema=SCHEMA, worker_result_sha256=pin,
            request_sha256=request_pin, process_identity=identity, worker_report_checked=True,
            retained_records=retained, observed_job_elapsed_seconds=observation.elapsed_seconds,
            observed_peak_process_commit_bytes=observation.job_peak_process_commit_bytes,
            observed_peak_job_commit_bytes=observation.job_peak_total_commit_bytes,
            whole_task_resources_verified=False, formal_execution_ready=False, formal_result=False))
        return report
    finally:
        lease.close()


def _validate_report(report, request_pin, plan):
    expected = set(('schema request_sha256 summary fresh_reopen_equal solver_calls_by_replay '
        'whole_task_resources_verified formal_execution_ready formal_result native_execution_authenticated').split())
    if (type(report) is not dict or set(report) != expected or report['schema'] != SCHEMA
            or report['request_sha256'] != request_pin or report['fresh_reopen_equal'] is not True
            or type(report['solver_calls_by_replay']) is not int or report['solver_calls_by_replay'] != 0
            or any(report[k] is not False for k in ('whole_task_resources_verified', 'formal_execution_ready',
                                                  'formal_result', 'native_execution_authenticated'))):
        raise ValueError('full Job report authority/binding mismatch')
    item = report['summary']
    fields = set(('status registry_head child_head stored_reports solver_calls projection_identity '
        'anchor_record_sha256 collector_identity resource_declaration_identity').split())
    if (type(item) is not dict or set(item) != fields or item['status'] not in ('accepted', 'rejected')
            or item['resource_declaration_identity'] != plan['declaration_identity']
            or type(item['stored_reports']) is not int or not 1 <= item['stored_reports'] <= plan['solver_calls']):
        raise ValueError('full Job terminal report inventory mismatch')
    for k in ('registry_head', 'child_head', 'anchor_record_sha256', 'collector_identity', 'resource_declaration_identity'):
        source.windows._sha(item[k])
    if item['status'] == 'accepted':
        source.windows._sha(item['projection_identity'])
        if (type(item['solver_calls']) is not int or item['solver_calls'] != plan['solver_calls']
                or item['stored_reports'] != plan['solver_calls']):
            raise ValueError('accepted report lacks complete stage inventory')
    elif item['solver_calls'] is not None or item['projection_identity'] is not None:
        raise ValueError('rejected report must preserve unknown calls and no projection')
