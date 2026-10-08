"""One-shot development controller for sequential execution and replay Jobs.

Resource observations and validated replay reports are not formal authority.
No assembly or solver assignment is materialized in this controller.
"""
from dataclasses import asdict, dataclass, fields, replace
from hashlib import sha256
import math
import os
from pathlib import Path
import stat
import time

from . import normal_task_worker_gurobi_licensed as worker, normal_task_process as process, normal_archive_capture_gurobi_direct as capture


journal, resources = worker.journal, process.resources
SCHEMA = 'draft_sequential_licensed_gurobi_direct_normal_task_controller_v1'
REPORT_LIMIT = 1024**2
METADATA_BYTES = 32*worker.PACKET_LIMIT


@dataclass(frozen=True)
class NormalTaskBudget:
    execute: process.TaskProcessBudget
    replay: process.TaskProcessBudget
    capture: capture.ArchiveCaptureBudget
    max_total_elapsed_seconds: float
    parent_tail_seconds: float
    max_controller_lifetime_peak_working_set_bytes: int
    controller_additional_commit_bytes: int
    commit_reserve_bytes: int
    archive_disk_bytes: int
    scratch_bytes_per_phase: int
    disk_reserve_bytes: int
    max_tree_entries: int

    def __post_init__(self):
        for value, cls in ((self.execute, process.TaskProcessBudget), (self.replay, process.TaskProcessBudget),
                           (self.capture, capture.ArchiveCaptureBudget)):
            if type(value) is not cls: raise ValueError('typed task phase budgets required')
            value.__post_init__()
        for name, ceiling in (('max_total_elapsed_seconds', 7200), ('parent_tail_seconds', 60)):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= ceiling:
                raise ValueError('finite bounded controller timing required')
        for name in ('max_controller_lifetime_peak_working_set_bytes', 'controller_additional_commit_bytes',
                     'commit_reserve_bytes', 'archive_disk_bytes', 'scratch_bytes_per_phase', 'disk_reserve_bytes',
                     'max_tree_entries'):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError('positive explicit controller resource budgets required')
        if self.max_tree_entries > 10000:
            raise ValueError('bounded task directory inventory required')


@dataclass(frozen=True)
class LicensedGurobiDirectNormalTaskObservation:
    controller_identity: str
    status: str
    stopped_phase: str
    error_type: str | None
    phases: tuple[process.TaskProcessObservation, ...]
    archive_pins: capture.GurobiDirectNormalArchivePins | None
    replay_report_sha256: str | None
    replay_status: str | None
    replay_errors: tuple[str, ...]
    accepted_record_reproduced: bool | None
    elapsed_seconds: float
    controller_lifetime_peak_working_set_bytes: int | None
    pre_final_observation_task_logical_bytes: int | None
    whole_task_resources_verified: bool = False
    hard_disk_quota_enforced: bool = False
    native_execution_authenticated: bool = False
    formal_result: bool = False


def _host(directory, budget, additional_commit, disk_bytes):
    return resources.HostResourceBudget(additional_commit, budget.commit_reserve_bytes,
        (resources.DirectoryDemand('task', str(directory), disk_bytes, budget.disk_reserve_bytes),))


def controller_identity(root, request, budget, environment):
    _plain_inputs(root, request, budget, environment)
    if type(budget) is not NormalTaskBudget or type(request) is not worker.LicensedGurobiDirectNormalTaskRequest:
        raise ValueError('typed complete task budget required')
    budget.__post_init__()
    if (request.max_replay_bytes > REPORT_LIMIT or budget.capture.max_record_bytes != request.max_record_bytes
            or budget.archive_disk_bytes < 2*budget.capture.max_database_bytes+request.max_replay_bytes+METADATA_BYTES):
        raise ValueError('controller report/capture/archive budgets disagree')
    root = journal.local._path(root)
    if not root.name.endswith('_non_authoritative') or not root.parent.is_dir():
        raise ValueError('new development task target with existing parent required')
    worker.codec._environment(environment)
    initial = _host(root.parent, budget,
        max(budget.execute.max_job_commit_bytes, budget.replay.max_job_commit_bytes)+budget.controller_additional_commit_bytes,
        budget.archive_disk_bytes+2*budget.scratch_bytes_per_phase)
    return sha256(journal._bytes((SCHEMA, str(root), worker.task_identity(request), asdict(budget), environment,
        resources.resource_identity(initial),
        tuple((str(Path(m.__file__).resolve()), sha256(Path(m.__file__).read_bytes()).hexdigest())
              for m in (worker, process, resources, capture)), sha256(Path(__file__).read_bytes()).hexdigest()))).hexdigest()


def _plain_inputs(root, request, budget, environment):
    """Reject callbacks/subclasses before any dataclass copy or path conversion."""
    allowed = (worker.LicensedGurobiDirectNormalTaskRequest, worker.inputs.legacy.NormalTaskSourceRequest,
        worker.kernel.Rq2ModelScale, worker.kernel.Rq2SolverSpec, worker.kernel.NormalExecutionBudget,
        NormalTaskBudget, process.TaskProcessBudget, capture.ArchiveCaptureBudget)
    def check(value):
        if type(value) in (str, int, float, bool, type(None)): return
        if type(value) not in allowed: raise ValueError('plain typed controller inputs required')
        for field in fields(value): check(getattr(value, field.name))
    if type(root) not in (str, type(Path())) or type(environment) is not dict:
        raise ValueError('plain controller path/environment required')
    if any(type(k) is not str or type(v) is not str for k, v in environment.items()):
        raise ValueError('plain controller environment strings required')
    check(request)
    check(budget)


def _tree_bytes(root, request, budget, deadline):
    """Bounded no-reparse inventory; logical bytes are not physical disk quota."""
    top_files = {'execution.lock', 'controller.request.json', 'controller.intent.json',
        'retained_pins.json', 'final_pins.json', 'capture.supervision.json', 'recapture.supervision.json',
        'controller.observation.json', 'replay.result.json'}
    for phase in ('execute', 'replay'):
        top_files.update(phase+'.'+suffix+'.json' for suffix in (
            'request', 'intent', 'supervision', 'launch', 'claim', 'complete', 'observation'))
    normal_files = {'execution.lock', 'normal.sqlite3', 'normal.sqlite3-journal',
        'normal.sqlite3-wal', 'normal.sqlite3-shm'}
    totals = dict(archive=0, execute=0, replay=0)
    pending, count = [(root, 'archive')], 0
    while pending:
        directory, area = pending.pop()
        directory = journal.local._path(directory)
        with os.scandir(directory) as entries:
            for entry in entries:
                item = Path(entry.path)
                deadline()
                count += 1
                if count > budget.max_tree_entries: raise ValueError('task tree entry budget exceeded')
                info = item.lstat()
                if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                    raise ValueError('task tree reparse entry refused')
                if stat.S_ISDIR(info.st_mode):
                    if directory == root:
                        if item.name not in ('normal_non_authoritative', 'execute_non_authoritative', 'replay_non_authoritative'):
                            raise ValueError('unexpected task directory')
                        next_area = item.name.split('_')[0] if item.name != 'normal_non_authoritative' else 'archive'
                    elif area != 'archive': next_area = area
                    else: raise ValueError('unexpected archive subdirectory')
                    pending.append((item, next_area))
                    continue
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise ValueError('regular single-link task files required')
                limit = budget.scratch_bytes_per_phase
                if directory == root:
                    if item.name not in top_files: raise ValueError('unexpected task file')
                    limit = request.max_replay_bytes if item.name == 'replay.result.json' else worker.PACKET_LIMIT
                    if item.name == 'execution.lock': limit = 1
                elif area == 'archive':
                    if item.name not in normal_files: raise ValueError('unexpected normal archive file')
                    limit = 1 if item.name == 'execution.lock' else budget.capture.max_database_bytes
                if info.st_size > limit: raise ValueError('task file byte budget exceeded')
                totals[area] += info.st_size
                if totals[area] > (budget.archive_disk_bytes if area == 'archive' else budget.scratch_bytes_per_phase):
                    raise ValueError('task directory logical byte budget exceeded')
    return sum(totals.values())


# Explicit report vocabulary of the pinned replay implementations.
NATIVE_REPLAY_ERRORS = frozenset((
    'assignment_flag_mismatch',
    'assignment_metric_without_single_solution',
    'assignment_without_single_solution',
    'canonical_completion_mismatch',
    'canonical_objective_or_residual_mismatch',
    'execution_error_projection_mismatch',
    'initial_assignment_mismatch',
    'initial_structure_mismatch',
    'model_scale_mismatch',
    'native_bound_projection_mismatch',
    'native_infeasible_flag_mismatch',
    'native_objective_mismatch',
    'native_return_without_one_recorded_call',
    'optimal_flag_mismatch',
    'partial_evidence_claims_complete_execution_flag',
    'purpose_mismatch',
    'single_solution_missing_loaded_assignment',
    'structure_inventory_mismatch',
    'structure_preload_runtime_or_options_mismatch',
))
SOURCE_REPLAY_ERRORS = frozenset((
    'accepted_builder_inventory_mismatch',
    'accepted_normal_missing_complete_replayed_evidence',
    'archived_post_binding_mismatch',
    'builder_inventory_mismatch',
    'core_evidence_size_mismatch',
    'fabricated_missing_return_error',
    'inner_call_completeness_mismatch',
    'inner_call_count_mismatch',
    'lifetime_peak_decreased',
    'missing_native_execution_error',
    'missing_pipeline_error',
    'missing_post_memory_error',
    'missing_return_error',
    'missing_witness_error',
    'native_builder_inventory_mismatch',
    'nested_builder_timing_mismatch',
    'normal_acceptance_flag_mismatch',
    'normal_status_mismatch',
    'normal_timing_order_mismatch',
    'normal_witness_mismatch',
    'outer_call_completeness_mismatch',
    'outer_call_count_mismatch',
    'post_source_error_phase_mismatch',
    'resource_error_projection_mismatch:core_evidence_payload_exceeds_budget',
    'resource_error_projection_mismatch:observed_wall_time_exceeds_budget',
    'resource_error_projection_mismatch:process_lifetime_peak_exceeds_budget',
    'source_acceptance_flag_mismatch',
    'source_binding_change_error_projection_mismatch',
    'source_changed_during_replay',
    'source_correspondence_flag_mismatch',
    'source_recorded_result_mismatch',
    'source_status_mismatch',
    'valid_assignment_builder_inventory_mismatch',
    'validation_error_without_inner_return',
    'witness_without_valid_raw_assignment',
    'wrapper_timing_order_mismatch',
))
DECLARED_REPLAY_ERRORS = frozenset((
    'declared_acceptance_flag_mismatch',
    'declared_accepted_without_replayed_source',
    'declared_call_completeness_mismatch',
    'declared_call_count_mismatch',
    'declared_recorded_result_mismatch',
    'declared_status_mismatch',
    'missing_source_return_count_not_unknown',
    'missing_source_return_error',
    'preparation_timing_sum_mismatch',
    'source_return_error_with_complete_source',
))


def _validate_errors(errors, markers, prefixes=()):
    if len(errors) != len(set(errors)):
        raise ValueError('duplicate replay error')
    for error in errors:
        if error in markers:
            continue
        prefix, separator, text = error.partition(':')
        if not separator or prefix not in prefixes or not text:
            raise ValueError('unknown replay error vocabulary')
    if any(sum(x.startswith(prefix+':') for x in errors) > 1 for prefix in prefixes):
        raise ValueError('duplicate replay exception phase')


def _source_report(values, pins, request):
    if type(values) is not dict or set(values) != {f.name for f in fields(worker.replay.GurobiDirectSourceRecordReplay)}:
        raise ValueError('exact nested source replay field inventory required')
    if type(values['errors']) is not list:
        raise ValueError('nested source replay error array required')
    values = dict(values, errors=tuple(values['errors']))
    booleans = ('source_input_binding_verified', 'archive_consistent', 'assignment_recomputed',
        'normal_witness_reproduced', 'recorded_source_accepted', 'accepted_record_reproduced',
        'native_execution_authenticated', 'resource_measurements_authenticated', 'resume_authorized',
        'formal_result', 'security_certified')
    if (any(type(values[name]) is not bool for name in booleans)
            or values['recorded_normal_accepted'] is not None and type(values['recorded_normal_accepted']) is not bool
            or type(values['errors']) is not tuple or any(type(error) is not str for error in values['errors'])
            or type(values['solver_calls_by_replay']) is not int or values['solver_calls_by_replay'] != 0
            or values['record_sha256'] != pins.record_sha256 or values['result_identity'] != pins.claimed_result_identity
            or values['replay_identity'] != request.expected_replay_identity
            or values['source_input_binding_verified'] is not True
            or any(values[name] is not False for name in ('native_execution_authenticated',
                'resource_measurements_authenticated', 'resume_authorized', 'formal_result', 'security_certified'))
            or values['optimality_certificate'] is not None or values['infeasibility_certificate'] is not None):
        raise ValueError('complete replay report identity/type/authority mismatch')
    _validate_errors(tuple(x for x in values['errors'] if not x.startswith('native:')), SOURCE_REPLAY_ERRORS)
    if values['native_record_scope'] not in ('no_native_record', 'complete_native_record', 'partial_execution_evidence'):
        raise ValueError('unknown replay report scope')
    diagnostic = None
    if (values['native_replay_json'] is None) is not (values['native_record_scope'] == 'no_native_record'):
        raise ValueError('nested replay diagnostic scope mismatch')
    if values['native_replay_json'] is not None:
        if type(values['native_replay_json']) is not str:
            raise ValueError('bounded native replay JSON required')
        diagnostic = journal._decoded(values['native_replay_json'].encode())
        required = {'model_structure_identity', 'scope', 'replay_consistent', 'assignment_recomputed',
            'canonical_assignment_valid', 'recomputed_objective', 'recomputed_maximum_residual',
            'recomputed_maximum_integrality_violation', 'reported_optimal', 'reported_native_infeasible',
            'optimal_flag_reproduced', 'native_infeasible_flag_reproduced', 'recorded_execution_errors', 'replay_errors'}
        if (type(diagnostic) is not dict or set(diagnostic) != required
                or diagnostic['scope'] != values['native_record_scope']
                or diagnostic['assignment_recomputed'] is not values['assignment_recomputed']
                or any(type(diagnostic[name]) is not bool for name in ('replay_consistent', 'assignment_recomputed',
                    'reported_optimal', 'reported_native_infeasible'))
                or any(diagnostic[name] is not None and type(diagnostic[name]) is not bool for name in (
                    'canonical_assignment_valid', 'optimal_flag_reproduced', 'native_infeasible_flag_reproduced'))
                or any(type(diagnostic[name]) is not list or any(type(x) is not str for x in diagnostic[name])
                    for name in ('recorded_execution_errors', 'replay_errors'))):
            raise ValueError('nested replay diagnostic inventory/type mismatch')
        _validate_errors(diagnostic['replay_errors'], NATIVE_REPLAY_ERRORS, ('native_metadata', 'assignment_replay'))
        worker.kernel._pin(diagnostic['model_structure_identity'])
        if diagnostic['replay_consistent'] is not (diagnostic['scope'] == 'complete_native_record' and not diagnostic['replay_errors']):
            raise ValueError('nested replay consistency mismatch')
        for name in ('recomputed_objective', 'recomputed_maximum_residual', 'recomputed_maximum_integrality_violation'):
            value = diagnostic[name]
            if value is not None and (type(value) is not float or not math.isfinite(value)):
                raise ValueError('finite nested replay measurements required')
    elif values['native_record_scope'] != 'no_native_record' or values['assignment_recomputed']:
        raise ValueError('missing nested replay diagnostic')
    native_errors = () if diagnostic is None else tuple('native:'+x for x in diagnostic['replay_errors'])
    if tuple(x for x in values['errors'] if x.startswith('native:')) != native_errors:
        raise ValueError('source/native replay error projection mismatch')
    consistent, accepted = not values['errors'], values['accepted_record_reproduced']
    status = 'inconsistent_normal_record' if not consistent else (
        'replayed_accepted_normal_record' if accepted else 'replayed_unresolved_normal_record')
    if (values['archive_consistent'] is not consistent or values['status'] != status
            or accepted is not (consistent and values['recorded_source_accepted'])
            or accepted and (not values['assignment_recomputed'] or not values['normal_witness_reproduced']
                or values['recorded_normal_accepted'] is not True or not values['recorded_source_accepted']
                or values['native_record_scope'] != 'complete_native_record' or diagnostic is None
                or diagnostic['replay_consistent'] is not True or diagnostic['optimal_flag_reproduced'] is not True
                or diagnostic['reported_optimal'] is not True or diagnostic['reported_native_infeasible'] is not False
                or diagnostic['native_infeasible_flag_reproduced'] is not False
                or any(diagnostic[name] is None for name in ('recomputed_objective', 'recomputed_maximum_residual',
                    'recomputed_maximum_integrality_violation'))
                or diagnostic['canonical_assignment_valid'] is not True or diagnostic['replay_errors'])):
        raise ValueError('replay report state inconsistent')
    return values


def _report(raw, pins, request, completion):
    wire = journal._decoded(raw)
    encoded = worker.replay._fields(wire, worker.replay.DeclaredGurobiDirectNormalRecordReplay)
    values = {name: worker.codec._decode(value) for name, value in encoded.items()}
    flags = ('archive_consistent', 'accepted_record_reproduced', 'source_input_binding_verified',
        'assignment_recomputed', 'normal_witness_reproduced', 'recorded_declared_accepted',
        'native_execution_authenticated', 'resource_measurements_authenticated', 'resume_authorized',
        'formal_result', 'security_certified')
    if (any(type(values[name]) is not bool for name in flags)
            or type(values['errors']) is not tuple or any(type(x) is not str for x in values['errors'])
            or type(values['solver_calls_by_replay']) is not int or values['solver_calls_by_replay'] != 0
            or values['record_sha256'] != pins.record_sha256 or values['result_identity'] != pins.claimed_result_identity
            or values['replay_identity'] != request.expected_replay_identity
            or values['source_input_binding_verified'] is not True
            or any(values[name] is not False for name in ('native_execution_authenticated',
                'resource_measurements_authenticated', 'resume_authorized', 'formal_result', 'security_certified'))
            or values['optimality_certificate'] is not None or values['infeasibility_certificate'] is not None):
        raise ValueError('declared replay report identity/type/authority mismatch')
    _validate_errors(tuple(x for x in values['errors'] if not x.startswith('source:')), DECLARED_REPLAY_ERRORS)
    nested = values['source_replay_json']
    source = None
    if nested is not None:
        if type(nested) is not str:
            raise ValueError('nested source replay JSON required')
        source = _source_report(journal._decoded(nested.encode()), pins, request)
    for name in ('assignment_recomputed', 'normal_witness_reproduced'):
        if values[name] is not (source is not None and source[name]):
            raise ValueError('declared/source replay projection mismatch')
    expected_source_errors = () if source is None else tuple('source:'+x for x in source['errors'])
    if tuple(x for x in values['errors'] if x.startswith('source:')) != expected_source_errors:
        raise ValueError('declared/source replay error projection mismatch')
    consistent = not values['errors']
    accepted = consistent and values['recorded_declared_accepted']
    status = 'inconsistent_declared_normal_record' if not consistent else (
        'replayed_accepted_declared_normal_record' if accepted else 'replayed_unresolved_declared_normal_record')
    if (values['archive_consistent'] is not consistent or values['accepted_record_reproduced'] is not accepted
            or values['status'] != status or accepted and (source is None or not source['accepted_record_reproduced'])):
        raise ValueError('declared replay report state inconsistent')
    expected = dict(replay_result_sha256=sha256(raw).hexdigest(), replay_result_bytes=len(raw),
        status=status, archive_consistent=consistent, accepted_record_reproduced=accepted)
    if journal._bytes(completion) != journal._bytes(expected):
        raise ValueError('small completion differs from complete declared replay report')
    return values


def supervise_normal_task(root, request, *, budget, environment, expected_controller_identity):
    started = time.monotonic()
    _plain_inputs(root, request, budget, environment)
    worker.kernel._pin(expected_controller_identity)
    request = worker.decode_request(journal._decoded(journal._bytes(asdict(request))))
    body = asdict(budget)
    body['execute'] = process.TaskProcessBudget(**body['execute'])
    body['replay'] = process.TaskProcessBudget(**body['replay'])
    body['capture'] = capture.ArchiveCaptureBudget(**body['capture'])
    budget, environment = NormalTaskBudget(**body), dict(environment)
    root = journal.local._path(root)
    if controller_identity(root, request, budget, environment) != expected_controller_identity:
        raise ValueError('external normal controller identity mismatch')
    initial = _host(root.parent, budget,
        max(budget.execute.max_job_commit_bytes, budget.replay.max_job_commit_bytes)+budget.controller_additional_commit_bytes,
        budget.archive_disk_bytes+2*budget.scratch_bytes_per_phase)
    if not resources.observe_headroom(initial, expected_request_identity=resources.resource_identity(initial)).observed_headroom_sufficient:
        raise ValueError('insufficient initial whole-task headroom')
    lease = object.__new__(journal.local._Lease)
    phases, pins, report_sha, report = [], None, None, None
    phase, peak, logical = 'initialize', None, None
    retained, directories = {}, {}
    failure = None

    def deadline():
        if time.monotonic()-started >= budget.max_total_elapsed_seconds:
            raise TimeoutError('whole task elapsed budget exceeded')

    def write(name, body):
        path = root/name
        worker._write(path, body)
        retained[path] = (journal.local._file_identity(path), sha256(journal._bytes(body)).hexdigest())

    def checkpoint():
        nonlocal peak, logical
        deadline()
        lease.check()
        for directory, identity in directories.items():
            info = journal.local._path(directory).stat()
            if (info.st_dev, info.st_ino) != identity: raise ValueError('private task directory replaced')
        if controller_identity(root, request, budget, environment) != expected_controller_identity:
            raise ValueError('controller implementation/request drift')
        for path, (identity, digest) in retained.items():
            if journal.local._file_identity(path) != identity: raise ValueError('controller file replaced')
            worker._read(path, digest)
        observed = resources.observe_headroom(initial, expected_request_identity=resources.resource_identity(initial))
        if process._reserve_errors(observed, initial): raise ValueError('controller host reserve breached')
        peak = worker.kernel._peak_working_set_bytes()
        if peak > budget.max_controller_lifetime_peak_working_set_bytes:
            raise ValueError('controller lifetime working-set observation exceeds declared ceiling')
        logical = _tree_bytes(root, request, budget, deadline)
        deadline()

    def run_phase(name, replay_pins=None):
        phase_budget = getattr(budget, name)
        tail = budget.parent_tail_seconds+budget.capture.max_elapsed_seconds
        if name == 'execute':
            tail += budget.capture.max_elapsed_seconds+budget.replay.max_elapsed_seconds+budget.replay.max_quiescence_seconds
        available = budget.max_total_elapsed_seconds-(time.monotonic()-started)-tail-phase_budget.max_quiescence_seconds
        if available <= 0: raise TimeoutError('insufficient remaining task phase time')
        effective = replace(phase_budget, max_elapsed_seconds=min(phase_budget.max_elapsed_seconds, available))
        scratch = root/(name+'_non_authoritative')
        phase_env = dict(environment, TEMP=str(scratch), TMP=str(scratch))
        raw = worker.phase_packet(root, name, request, phase_env,
            expected_task_identity=worker.task_identity(request), replay_pins=replay_pins)
        packet = journal._decoded(raw)
        write(name+'.request.json', packet)
        digest = sha256(raw).hexdigest()
        intent = dict(schema=worker.SCHEMA, phase=name, packet_sha256=digest, task_identity=packet['task_identity'])
        write(name+'.intent.json', intent)
        argv = worker.worker_argv(root/(name+'.request.json'), digest)
        archive_demand = budget.archive_disk_bytes if name == 'execute' else request.max_replay_bytes+METADATA_BYTES
        host = resources.HostResourceBudget(effective.max_job_commit_bytes, budget.commit_reserve_bytes, (
            resources.DirectoryDemand('archive', str(root), archive_demand, budget.disk_reserve_bytes),
            resources.DirectoryDemand('scratch', str(scratch), budget.scratch_bytes_per_phase, budget.disk_reserve_bytes)))
        host_pin = resources.resource_identity(host)
        arguments = dict(cwd=scratch, environment=phase_env, budget=effective, host_budget=host,
            expected_host_identity=host_pin)
        process_pin = process.task_process_identity(argv, **arguments)
        write(name+'.supervision.json', dict(controller_identity=expected_controller_identity,
            intent_sha256=sha256(journal._bytes(intent)).hexdigest(), process_identity=process_pin,
            budget=asdict(effective), host_budget=asdict(host), host_identity=host_pin))
        checkpoint()
        if budget.max_total_elapsed_seconds-(time.monotonic()-started) < effective.max_elapsed_seconds+effective.max_quiescence_seconds+tail:
            raise TimeoutError('remaining phase reservation consumed before spawn')
        with process.normal_task_child(argv, expected_process_identity=process_pin, **arguments) as child:
            launch = dict(**intent, pid=child.pid, creation_filetime=child.creation_filetime,
                argv_sha256=sha256(journal._bytes(argv)).hexdigest(),
                root_identity=list(lease.root_identity), scratch_identity=[scratch.stat().st_dev, scratch.stat().st_ino])
            write(name+'.launch.json', launch)
            child.release()
            observed = child.wait()
            if (type(observed) is not process.TaskProcessObservation
                    or observed.process_identity != process_pin
                    or type(observed.pid) is not int or observed.pid != launch['pid']
                    or type(observed.creation_filetime) is not int or observed.creation_filetime != launch['creation_filetime']
                    or observed.whole_job_quiescent is not True or observed.job_commit_limits_configured is not True
                    or any(getattr(observed, name) is not False for name in ('hard_disk_quota_enforced',
                        'whole_task_resources_verified', 'numerical_evidence_verified', 'formal_result'))):
                raise ValueError('task process observation identity/authority/quiescence mismatch')
        phases.append(observed)
        write(name+'.observation.json', asdict(observed))
        checkpoint()
        if observed.reason != 'child_exited' or type(observed.exit_code) is not int or observed.exit_code != 0:
            raise ValueError('task phase did not finish with a normal zero exit')
        claim = dict(**intent, pid=observed.pid, launch_sha256=sha256(journal._bytes(launch)).hexdigest())
        for suffix in ('claim', 'complete'):
            path = root/(name+'.'+suffix+'.json')
            body = worker._read(path)
            if suffix == 'claim': expected = claim
            else:
                if type(body) is not dict or 'completion' not in body:
                    raise ValueError('complete phase artifact required')
                expected = dict(**claim, completion=body['completion'], numerical_acceptance_by_controller=False, formal_result=False)
            if journal._bytes(body) != journal._bytes(expected): raise ValueError('phase claim/completion differs from launch')
            retained[path] = (journal.local._file_identity(path), sha256(journal._bytes(body)).hexdigest())
        return body['completion']

    def capture_phase(name, execution):
        tail = budget.parent_tail_seconds
        if name == 'capture':
            tail += budget.capture.max_elapsed_seconds+budget.replay.max_elapsed_seconds+budget.replay.max_quiescence_seconds
        if budget.max_total_elapsed_seconds-(time.monotonic()-started) < tail+budget.capture.max_elapsed_seconds:
            raise TimeoutError('insufficient remaining full archive capture reservation')
        arguments = dict(budget=budget.capture, expected_store_identity=execution['store_identity'],
            expected_declared_execution_identity=request.expected_declared_execution_identity,
            claimed_result_identity=execution['claimed_result_identity'])
        normal_root = root/'normal_non_authoritative'
        pin = capture.capture_identity(normal_root, **arguments)
        write(name+'.supervision.json', dict(controller_identity=expected_controller_identity,
            capture_identity=pin, budget=asdict(budget.capture),
            expected_store_identity=execution['store_identity'],
            expected_declared_execution_identity=request.expected_declared_execution_identity,
            claimed_result_identity=execution['claimed_result_identity']))
        checkpoint()
        if budget.max_total_elapsed_seconds-(time.monotonic()-started) < tail+budget.capture.max_elapsed_seconds:
            raise TimeoutError('archive capture reservation consumed before read')
        found = capture.capture_normal_archive(normal_root, expected_capture_identity=pin, **arguments)
        if (type(found) is not capture.GurobiDirectNormalArchivePins or found.capture_identity != pin
                or found.store_identity != execution['store_identity']
                or found.claimed_result_identity != execution['claimed_result_identity']
                or found.status != 'opaque_record_captured' or found.head == found.genesis
                or found.head != execution['head'] or found.record_sha256 != execution['record_sha256']
                or type(found.record_bytes) is not int or not 0 < found.record_bytes <= budget.capture.max_record_bytes
                or found.intent_present is not True
                or any(getattr(found, flag) is not False for flag in ('result_identity_verified',
                    'numerical_evidence_replayed', 'native_execution_authenticated', 'whole_job_quiescence_verified', 'formal_result'))):
            raise ValueError('execution completion differs from independently captured archive')
        worker.kernel._pin(found.genesis)
        deadline()
        return found

    try:
        # create=True refuses all existing roots, including partial old attempts.
        deadline()
        journal.local._Lease.__init__(lease, root, True)
        for name in ('execute', 'replay'):
            directory = root/(name+'_non_authoritative')
            directory.mkdir()
            info = directory.stat()
            directories[directory] = info.st_dev, info.st_ino
        try:
            write('controller.request.json', dict(schema=SCHEMA, controller_identity=expected_controller_identity,
                request=asdict(request), budget=asdict(budget), environment=environment, root_identity=list(lease.root_identity)))
            write('controller.intent.json', dict(schema=SCHEMA, controller_identity=expected_controller_identity,
                request_sha256=retained[root/'controller.request.json'][1]))
            checkpoint()
            phase = 'execute'
            completion = run_phase(phase)
            if type(completion) is not dict or set(completion) != {'store_identity', 'head', 'record_sha256', 'claimed_result_identity'}:
                raise ValueError('exact execution completion pins required')
            for value in completion.values(): worker.kernel._pin(value)
            execution = completion
            phase = 'capture'
            pins = capture_phase(phase, execution)
            write('retained_pins.json', asdict(pins))
            checkpoint()
            phase = 'replay'
            completion = run_phase(phase, dict(store_identity=pins.store_identity, head=pins.head,
                record_sha256=pins.record_sha256, claimed_result_identity=pins.claimed_result_identity))
            phase = 'report'
            path = root/'replay.result.json'
            identity = journal.local._file_identity(path)
            with path.open('rb') as stream: raw = stream.read(request.max_replay_bytes+1)
            if len(raw) > request.max_replay_bytes: raise ValueError('controller replay report byte budget exceeded')
            report = _report(raw, pins, request, completion)
            report_sha = sha256(raw).hexdigest()
            phase = 'recapture'
            final_pins = capture_phase(phase, execution)
            if journal._bytes(asdict(final_pins)) != journal._bytes(asdict(pins)):
                raise ValueError('normal archive changed after replay')
            write('final_pins.json', asdict(final_pins))
            phase = 'report'
            checkpoint()
            with path.open('rb') as stream: reread = stream.read(request.max_replay_bytes+1)
            if (len(reread) > request.max_replay_bytes or journal.local._file_identity(path) != identity
                    or sha256(reread).hexdigest() != report_sha):
                raise ValueError('replay report changed during controller validation')
            deadline()
            status, error_type = 'validated_before_final_observation_write', None
        except Exception as error:
            failure = error
            status, error_type = 'unresolved_task_attempt', type(error).__name__[:128]
        outcome = LicensedGurobiDirectNormalTaskObservation(expected_controller_identity, status, phase, error_type, tuple(phases), pins,
            report_sha, None if report is None else report['status'], () if report is None else report['errors'],
            None if report is None else report['accepted_record_reproduced'], time.monotonic()-started, peak, logical)
        try:
            if failure is None: deadline()
            write('controller.observation.json', asdict(outcome))
            if failure is None:
                finished = time.monotonic()-started
                if finished >= budget.max_total_elapsed_seconds:
                    raise TimeoutError('whole task elapsed budget exceeded')
        except Exception:
            if failure is not None: raise failure
            raise
        return replace(outcome, status='completed_development_replay_diagnostic',
            elapsed_seconds=finished) if failure is None else outcome
    finally:
        if getattr(lease, 'stream', None) is not None: lease.close()
