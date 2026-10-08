"""One-shot execute/audit pipeline; declared coverage is not resource certification."""
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
from math import isfinite
import os
from pathlib import Path
import stat
import sys
import time

from . import scale_episode_bidirectional_worker as worker
from . import declared_task_process as declared

base = worker.controller
process, local = base.process, base.local
SCHEMA = 'draft_bidirectional_mixed_selector_episode_pipeline_v1'


@dataclass(frozen=True)
class PipelineBudget:
    execute: process.TaskProcessBudget
    audit: process.TaskProcessBudget
    controller_seconds: int
    execute_scratch_bytes: int
    audit_scratch_bytes: int
    max_supervisor_peak_working_set_bytes: int
    max_tree_entries: int
    max_outer_scratch_entries: int


def admit(inputs, allocation):
    worker.transport.validate(inputs)
    if type(allocation) is not PipelineBudget:
        raise ValueError('typed pipeline budget required')
    for b in (allocation.execute, allocation.audit):
        if type(b) not in (process.TaskProcessBudget, declared.DeclaredTaskProcessBudget):
            raise ValueError('typed worker budget required')
        b.__post_init__()
        if type(b) is declared.DeclaredTaskProcessBudget and (
                b.resource_contract_identity != inputs.reference_request.budget.resource_contract_identity
                or b.envelope != inputs.budget.envelope):
            raise ValueError('outer process budget differs from original episode resource declaration')
    for name in ('controller_seconds', 'execute_scratch_bytes', 'audit_scratch_bytes',
                 'max_supervisor_peak_working_set_bytes', 'max_tree_entries', 'max_outer_scratch_entries'):
        if type(getattr(allocation, name)) is not int or getattr(allocation, name) <= 0:
            raise ValueError('positive pipeline allocation required')
    if allocation.max_tree_entries < inputs.budget.max_tree_entries+14+allocation.max_outer_scratch_entries:
        raise ValueError('pipeline entry allocation does not cover episode and outer scratch')
    b, envelope = inputs.budget, inputs.budget.envelope
    phase_count = 5*len(inputs.hours)
    execute_minimum = worker.episode.resources.admit(b, inputs.reference_request, inputs.arms, inputs.hours)
    wall = sum(x.max_elapsed_seconds+x.max_quiescence_seconds for x in (allocation.execute, allocation.audit))
    if allocation.execute.max_elapsed_seconds < execute_minimum or wall+allocation.controller_seconds > envelope.max_wall_seconds:
        raise ValueError('pipeline wall allocation does not cover complete execute/audit')
    if (allocation.execute.max_job_commit_bytes < b.controller_additional_commit_bytes+b.task_process_budget.max_job_commit_bytes
            or max(allocation.execute.max_job_commit_bytes, allocation.audit.max_job_commit_bytes) > envelope.max_job_commit_bytes):
        raise ValueError('pipeline Job allocation differs from complete envelope')
    # Input + result + two sets of intent/launch/observation/receipt and root lock.
    outer_metadata = 10*base.LIMIT+1
    episode_metadata = (1+2*len(inputs.hours))*base.LIMIT+1
    if (envelope.archive_bytes < phase_count*b.archive_bytes_per_task+episode_metadata+outer_metadata
            or envelope.scratch_bytes < phase_count*b.scratch_bytes_per_task
                +allocation.execute_scratch_bytes+allocation.audit_scratch_bytes):
        raise ValueError('pipeline archive/scratch allocation shortfall')


def _host(root, inputs, allocation, scratch=None, usage=None):
    e, serial = inputs.budget.envelope, inputs.resource_plan.serial_budget
    total = e.archive_bytes+e.scratch_bytes
    if usage is not None:
        total -= usage['archive_logical_bytes']+usage['scratch_logical_bytes']
    directories = (process.resources.DirectoryDemand('pipeline', str(root), total, serial.disk_reserve_bytes),)
    if scratch is not None:
        amount = allocation.execute_scratch_bytes if scratch.name == 'execute_scratch' else allocation.audit_scratch_bytes
        if usage is not None: amount -= usage[scratch.name+'_logical_bytes']
        if total < amount: raise ValueError('remaining disk allocation cannot cover worker scratch')
        directories = (process.resources.DirectoryDemand('pipeline', str(root), max(1, total-amount), serial.disk_reserve_bytes),
                       process.resources.DirectoryDemand('worker_scratch', str(scratch), max(1, amount), serial.disk_reserve_bytes))
    return process.resources.HostResourceBudget(e.max_job_commit_bytes+serial.supervisor_additional_commit_bytes,
                                               serial.commit_reserve_bytes, directories)


def controller_identity(root, inputs, *, allocation, environment):
    root = local._path(root)
    if not root.name.endswith('_non_authoritative'): raise ValueError('non_authoritative pipeline root required')
    admit(inputs, allocation)
    if type(environment) is not dict: raise ValueError('explicit pipeline environment required')
    process.process._environment_block(environment)
    packet = worker.transport.export_inputs(inputs)
    host = _host(root.parent, inputs, allocation)
    return worker.episode.tx.legacy._identity(SCHEMA, str(root), sha256(packet).hexdigest(), asdict(allocation),
        environment, process.resources.resource_identity(host), worker.implementation_identity(),
        str(Path(sys.executable).resolve()), sha256(Path(sys.executable).read_bytes()).hexdigest(),
        sha256(Path(declared.__file__).read_bytes()).hexdigest(),
        sha256(Path(__file__).read_bytes()).hexdigest())


def _measure(root, inputs, allocation, started, extra=0):
    envelope = inputs.budget.envelope
    def elapsed():
        value = time.monotonic()-started
        if value >= envelope.max_wall_seconds: raise TimeoutError('pipeline sampled deadline exceeded')
        return value
    elapsed()
    peak = worker.episode.resources.memory._peak_working_set_bytes()
    if peak > allocation.max_supervisor_peak_working_set_bytes:
        raise ValueError('pipeline supervisor working set exceeds declaration')
    count, archive, scratch, outer_entries, pending = 0, 0, 0, 0, [root]
    outer_bytes = dict(execute_scratch=0, audit_scratch=0)
    while pending:
        directory = local._path(pending.pop())
        with os.scandir(directory) as entries:
            for entry in entries:
                elapsed()
                count += 1
                if count+bool(extra) > allocation.max_tree_entries: raise ValueError('pipeline tree limit exceeded')
                path = Path(entry.path)
                parts = path.relative_to(root).parts
                if len(parts) > 1 and parts[0] in ('execute_scratch', 'audit_scratch'):
                    outer_entries += 1
                    if outer_entries > allocation.max_outer_scratch_entries:
                        raise ValueError('outer scratch entry allocation exceeded')
                info = path.lstat()
                if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                    raise ValueError('pipeline reparse refused')
                if stat.S_ISDIR(info.st_mode): pending.append(path)
                elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                    parts = path.relative_to(root).parts
                    is_scratch = parts[0] in ('execute_scratch', 'audit_scratch') or (
                        len(parts) >= 4 and parts[0] == 'episode_non_authoritative' and parts[2] == 'scratch')
                    if is_scratch: scratch += info.st_size
                    else: archive += info.st_size
                    if parts[0] in outer_bytes: outer_bytes[parts[0]] += info.st_size
                else: raise ValueError('pipeline regular single-link files required')
    if archive+extra > envelope.archive_bytes or scratch > envelope.scratch_bytes:
        raise ValueError('pipeline cumulative byte cap exceeded')
    if any(outer_bytes[name] > getattr(allocation, name+'_bytes') for name in outer_bytes):
        raise ValueError('worker scratch byte allocation exceeded')
    return dict(elapsed_seconds=elapsed(), supervisor_lifetime_peak_working_set_bytes=peak,
                archive_logical_bytes=archive, scratch_logical_bytes=scratch, tree_entries=count,
                **{name+'_logical_bytes': value for name, value in outer_bytes.items()},
                hard_parent_wall_limit=False, hard_parent_commit_limit=False, hard_disk_quota=False)


def _successful_observation(observed, budget, host):
    if (observed.reason != 'child_exited' or type(observed.exit_code) is not int or observed.exit_code != 0
            or observed.last_resource_errors != () or observed.observation_error_type is not None
            or observed.stop_markers != ('direct_child_exit_observed',)
            or observed.whole_job_quiescent is not True or observed.job_commit_limits_configured is not True
            or any(getattr(observed, k) is not False for k in ('hard_disk_quota_enforced',
                     'whole_task_resources_verified', 'numerical_evidence_verified', 'formal_result'))):
        raise ValueError('pipeline worker did not complete; task remains unresolved')
    for name, ceiling in (('pid', None), ('creation_filetime', None), ('runtime_samples', None),
                          ('job_peak_process_commit_bytes', budget.max_process_commit_bytes),
                          ('job_peak_total_commit_bytes', budget.max_job_commit_bytes)):
        value = getattr(observed, name)
        if type(value) is not int or value <= 0 or (ceiling is not None and value > ceiling):
            raise ValueError('invalid pipeline process measurement')
    if (observed.job_peak_process_commit_bytes > observed.job_peak_total_commit_bytes
            or type(observed.elapsed_seconds) not in (int, float) or not isfinite(observed.elapsed_seconds)
            or not 0 <= observed.elapsed_seconds <= budget.max_elapsed_seconds+budget.max_quiescence_seconds
            or type(observed.minimum_runtime_commit_available_bytes) is not int
            or observed.minimum_runtime_commit_available_bytes < host.commit_reserve_bytes):
        raise ValueError('invalid pipeline time/commit observation')
    disks = observed.minimum_runtime_disk_available_bytes
    volumes = {process.resources._directory_binding(d.directory)[3] for d in host.directories}
    if (type(disks) is not tuple or any(type(p) is not tuple or len(p) != 2 or type(p[0]) is not str
            or type(p[1]) is not int or p[1] < max(d.reserve_bytes for d in host.directories) for p in disks)
            or tuple(v for v, _ in disks) != tuple(sorted(volumes))):
        raise ValueError('invalid pipeline disk observation')


def supervise_episode(root, inputs, *, allocation, environment, expected_controller_identity):
    started = time.monotonic()
    inputs, allocation, environment = deepcopy((inputs, allocation, environment))
    root = local._path(root)
    def identity_check():
        if controller_identity(root, inputs, allocation=allocation, environment=environment) != expected_controller_identity:
            raise ValueError('episode pipeline input/implementation drift')
    identity_check()
    lease = object.__new__(local._Lease)
    retained = {}
    episode_files = None
    evidence_lease = None
    worker_elapsed, active_started = 0., None
    def snapshot():
        return {str(p.relative_to(episode_root)): worker.episode._file_pin(p)
                for p in episode_root.rglob('*') if p.is_file() and p != episode_root/'execution.lock'}
    def check():
        lease.check()
        identity_check()
        for path, (identity, digest) in retained.items():
            if sha256(base.worker.store._bytes(base._read(path, identity))).hexdigest() != digest:
                raise ValueError('pipeline retained record drift')
        measurement = _measure(root, inputs, allocation, started)
        if episode_files is not None:
            current_lease = evidence_lease or local._Lease(episode_root, False)
            try:
                current_lease.check()
                if snapshot() != episode_files: raise ValueError('episode evidence changed across pipeline phases')
            finally:
                if current_lease is not evidence_lease: current_lease.close()
        now = time.monotonic()
        controller_elapsed = now-started-worker_elapsed-(0. if active_started is None else now-active_started)
        if controller_elapsed > allocation.controller_seconds:
            raise TimeoutError('pipeline controller allowance exceeded')
        measurement['controller_elapsed_seconds'] = controller_elapsed
        return measurement
    def write(name, value):
        _measure(root, inputs, allocation, started, len(base.worker.store._bytes(value)))
        retained[root/name] = base._write(root/name, value)
    try:
        initial_host = _host(root.parent, inputs, allocation)
        if not process.resources.observe_headroom(initial_host,
                expected_request_identity=process.resources.resource_identity(initial_host)).observed_headroom_sufficient:
            raise ValueError('pipeline initial headroom insufficient')
        local._Lease.__init__(lease, root, True)
        execute_scratch, audit_scratch = root/'execute_scratch', root/'audit_scratch'
        execute_scratch.mkdir()
        audit_scratch.mkdir()
        packet = worker.transport.export_inputs(inputs)
        request_pin, impl = sha256(packet).hexdigest(), worker.implementation_identity()
        write('request.json', base.worker.store._decoded(packet))
        episode_root = root/'episode_non_authoritative'
        episode_environment = dict(environment, TEMP=str(execute_scratch), TMP=str(execute_scratch))
        environment_pin = sha256(base.worker.store._bytes(episode_environment)).hexdigest()
        phases, pins = [], None
        for mode, budget, scratch in (('execute', allocation.execute, execute_scratch), ('audit', allocation.audit, audit_scratch)):
            sampled = check()
            remaining = (allocation.execute, allocation.audit) if mode == 'execute' else (allocation.audit,)
            required = sum(b.max_elapsed_seconds+b.max_quiescence_seconds for b in remaining)
            required += max(0., allocation.controller_seconds-sampled['controller_elapsed_seconds'])
            if inputs.budget.envelope.max_wall_seconds-(time.monotonic()-started) < required:
                raise TimeoutError('pipeline remaining wall cannot cover next worker')
            receipt = root/(mode+'_receipt_non_authoritative.json')
            argv = [str(Path(sys.executable).resolve()), '-I', '-B', str(Path(worker.__file__).resolve()),
                '--mode', mode, '--request-path', str(root/'request.json'), '--expected-request-sha256', request_pin,
                '--max-request-bytes', str(worker.transport.LIMIT), '--episode-root', str(episode_root),
                '--receipt-path', str(receipt), '--episode-environment-directory', str(execute_scratch),
                '--expected-environment-sha256', environment_pin, '--expected-implementation-identity', impl]
            if pins is not None:
                argv += ['--header-sha256', pins['header_sha256']]
                for name in ('intent', 'result'):
                    for pin in pins[name+'_sha256s']: argv += ['--'+name+'-sha256', pin]
            host = _host(root, inputs, allocation, scratch, sampled)
            phase = dict(cwd=scratch, environment=dict(environment, TEMP=str(scratch), TMP=str(scratch)),
                budget=budget, host_budget=host, expected_host_identity=process.resources.resource_identity(host))
            identity_api, child_api = ((declared.task_process_identity, declared.declared_task_child)
                if type(budget) is declared.DeclaredTaskProcessBudget else (process.task_process_identity, process.normal_task_child))
            pin = identity_api(argv, **phase)
            write(mode+'_intent.json', dict(schema=SCHEMA, mode=mode, controller_identity=expected_controller_identity,
                request_sha256=request_pin, process_identity=pin, worker_identity=impl, audit_pins=pins,
                allocation=asdict(allocation), host_budget=asdict(host), formal_result=False))
            check()
            with child_api(argv, expected_process_identity=pin, **phase) as child:
                active_started = child._started
                write(mode+'_launch.json', dict(process_identity=pin, pid=child.pid, creation_filetime=child.creation_filetime))
                check()
                child.release()
                observed = child.wait()
                if (type(observed) is not process.TaskProcessObservation or observed.process_identity != pin
                        or observed.pid != child.pid or observed.creation_filetime != child.creation_filetime
                        or observed.whole_job_quiescent is not True):
                    raise ValueError('pipeline worker identity/quiescence unverified')
                if type(observed.elapsed_seconds) not in (int, float) or not isfinite(observed.elapsed_seconds) or observed.elapsed_seconds < 0:
                    raise ValueError('invalid worker lifecycle time')
                worker_elapsed += observed.elapsed_seconds
                active_started = None
            write(mode+'_observation.json', asdict(observed))
            check()
            _successful_observation(observed, budget, host)
            if mode == 'audit':
                evidence_lease = local._Lease(episode_root, False)
                check()
            file_pin = worker.episode._file_pin(receipt)
            body = base._read(receipt, file_pin[0])
            if (sha256(base.worker.store._bytes(body)).hexdigest() != file_pin[1]
                    or set(body) != {'schema', 'mode', 'request_sha256', 'implementation_identity', 'environment_sha256',
                                     'episode_root', 'audit_pins', 'outcome', 'formal_result', 'whole_task_resources_verified',
                                     'executable_resume_available'}
                    or body['schema'] != worker.SCHEMA or body['mode'] != mode or body['request_sha256'] != request_pin
                    or body['implementation_identity'] != impl or body['environment_sha256'] != environment_pin
                    or body['episode_root'] != str(episode_root)
                    or base.worker.store._bytes(body['audit_pins']) != base.worker.store._bytes(pins)
                    or any(body[k] is not False for k in ('formal_result', 'whole_task_resources_verified', 'executable_resume_available'))):
                raise ValueError('pipeline worker receipt binding mismatch')
            retained[receipt] = file_pin
            outcome = body['outcome']
            if mode == 'execute':
                if (set(outcome) != {'observation_window_consumed', 'completed_hours', 'header_sha256', 'intent_sha256s', 'result_sha256s'}
                        or outcome['observation_window_consumed'] is not True
                        or type(outcome['completed_hours']) is not int or outcome['completed_hours'] != len(inputs.hours)
                        or len(outcome['intent_sha256s']) != len(inputs.hours) or len(outcome['result_sha256s']) != len(inputs.hours)):
                    raise ValueError('pipeline execution receipt inventory mismatch')
                pins = {key: outcome[key] for key in ('header_sha256', 'intent_sha256s', 'result_sha256s')}
                for item in (pins['header_sha256'], *pins['intent_sha256s'], *pins['result_sha256s']):
                    worker.transport.selector.scale.actual._hash(item)
                proof_lease = local._Lease(episode_root, False)
                try:
                    _measure(root, inputs, allocation, started)
                    episode_files = snapshot()
                    expected = {'header.json': pins['header_sha256']}
                    for kind in ('intent', 'result'):
                        expected.update({f'{i:06d}.{kind}.json': value for i, value in enumerate(pins[kind+'_sha256s'])})
                    if any(episode_files.get(name, (None, None))[1] != digest for name, digest in expected.items()):
                        raise ValueError('execute receipt differs from saved episode pins')
                    proof_lease.check()
                finally:
                    proof_lease.close()
            else:
                selected = unresolved = 0
                for index in range(len(inputs.hours)):
                    hour = base._read(episode_root/f'{index:06d}.result.json')
                    for i, evidence in enumerate(hour['phase_evidence']):
                        if evidence['status'] != 'returned_unverified': continue
                        name = f'{index:06d}_reference_non_authoritative' if i == 0 else f'{index:06d}_actual_{i-1}_non_authoritative'
                        phase_receipt = base._read(episode_root/name/'receipt_non_authoritative.json')
                        if phase_receipt['reported_status'] == 'selected': selected += 1
                        else: unresolved += 1
                expected = dict(schema=worker.replay.SCHEMA, status='reproduced_hour_prefix', completed_hours=len(inputs.hours),
                    planned_hours=len(inputs.hours), pending_intent=False, reserved_solver_calls=inputs.budget.max_solver_calls,
                    reserved_solver_seconds=inputs.budget.max_solver_seconds, selected_phase_chains_replayed=selected,
                    unresolved_phase_records=unresolved, unresolved_numerical_details_replayed=False,
                    observation_window_consumed=True, solver_calls_by_auditor=0, native_execution_authenticated=False,
                    whole_job_quiescence_verified=False, complete_service_certified=False, formal_result=False,
                    executable_resume_available=False)
                if base.worker.store._bytes(outcome) != base.worker.store._bytes(expected):
                    raise ValueError('pipeline audit did not reproduce exact observed window report')
            phases.append(dict(mode=mode, process_identity=pin, receipt_sha256=file_pin[1], observation=asdict(observed)))
            check()
        measurement = check()
        result = dict(schema=SCHEMA, controller_identity=expected_controller_identity,
            status='observed_window_replayed', phases=phases, episode_pins=pins, audit=outcome,
            resource_sample=measurement, formal_result=False, whole_task_resources_verified=False,
            complete_service_certified=False, executable_resume_available=False)
        write('result.json', result)
        check()
        return result
    finally:
        try:
            if evidence_lease is not None: evidence_lease.close()
        finally:
            if getattr(lease, 'stream', None) is not None: lease.close()
