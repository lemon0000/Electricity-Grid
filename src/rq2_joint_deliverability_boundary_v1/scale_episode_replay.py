"""Read-only, solver-free audit of a pinned scale-episode prefix; no resume."""
from copy import deepcopy
from dataclasses import asdict, replace, fields
from hashlib import sha256
from pathlib import Path
import sys
from math import isfinite

from . import scale_episode as episode

tx, controller = episode.tx, episode.controller
SCHEMA = 'draft_scale_episode_offline_audit_v1'


def implementation_identity():
    return tx.legacy._identity(SCHEMA, episode._implementation(), sha256(Path(__file__).read_bytes()).hexdigest())


def _same(left, right):
    return controller.worker.store._bytes(left) == controller.worker.store._bytes(right)


def audit_episode(root, reference_request, arms, hours, *, budget, environment, resource_plan,
                  expected_header_sha256, expected_intent_sha256s, expected_result_sha256s,
                  expected_audit_identity):
    """Independent typed inputs and externally retained prefix pins are required.

    Process observations are checked as records, not authenticated OS history.
    A final pending intent is charged in full and never read as a failed solve.
    """
    request0, setups, window, budget, environment = deepcopy((reference_request, arms, hours, budget, environment))
    resource_plan = deepcopy(resource_plan)
    if expected_audit_identity != implementation_identity():
        raise ValueError('external audit implementation mismatch')
    episode._fairness(setups)
    if type(budget) is not episode.EpisodeBudget:
        raise ValueError('typed episode budget required')
    budget.__post_init__()
    if type(window) is not tuple or not window or any(type(h) is not episode.HourInput for h in window):
        raise ValueError('typed complete input window required')
    if type(expected_intent_sha256s) is not tuple or type(expected_result_sha256s) is not tuple:
        raise ValueError('independent ordered prefix pins required')
    n, m = len(expected_intent_sha256s), len(expected_result_sha256s)
    if not m <= n <= len(window) or n-m not in (0, 1):
        raise ValueError('completed prefix with at most one pending intent required')
    for pin in (expected_header_sha256, *expected_intent_sha256s, *expected_result_sha256s):
        tx.replay.scale.actual._hash(pin)
    controller.process.process._environment_block(environment)
    budgets = (request0.budget, *(a.budget for a in setups))
    calls, seconds = sum(b.max_solver_calls for b in budgets), sum(b.max_total_solver_seconds for b in budgets)
    start = request0.budget.source_hour
    if (request0.budget.role != 'reference'
            or request0.info != window[0].info or request0.disclosure != window[0].disclosure
            or tuple(h.info.current.source_hour for h in window) != tuple(range(start, start+len(window)))
            or calls*len(window) > budget.max_solver_calls or seconds*len(window) > budget.max_solver_seconds):
        raise ValueError('independent episode declarations disagree')
    for b in budgets:
        b.__post_init__()
        if (b.source_hour != start or b.task_id != request0.budget.task_id
                or b.resource_contract_identity != request0.budget.resource_contract_identity
                or b.generator_uids != request0.budget.generator_uids
                or b.max_total_solver_seconds > budget.task_process_budget.max_elapsed_seconds):
            raise ValueError('inconsistent task/role/resource reservation')
    episode.resources.admit(budget, request0, setups, window)
    episode.resources.bind_plan(resource_plan, budget, request0, setups, window)
    impl = episode._implementation()
    lease = controller.local._Lease(root, False)
    retained = {}
    selected_phases = unresolved_phases = 0
    consumed_tasks = set()
    def read(path, pin=None):
        body = controller._read(path)
        observed = episode._file_pin(path)
        digest = sha256(controller.worker.store._bytes(body)).hexdigest()
        if observed[1] != digest or (pin is not None and digest != pin):
            raise ValueError('episode artifact digest/crosslink mismatch')
        retained[path] = observed
        return body
    def check():
        lease.check()
        if episode._implementation() != impl or implementation_identity() != expected_audit_identity:
            raise ValueError('episode replay implementation drift')
        for path, pin in retained.items():
            if episode._file_pin(path) != pin:
                raise ValueError('episode artifact changed during replay')
    def phase(index, role, request, saved):
        nonlocal selected_phases, unresolved_phases
        name = f'{index:06d}_reference_non_authoritative' if role == 'reference' else f'{index:06d}_actual_{role[-1]}_non_authoritative'
        task = lease.root/name
        consumed_tasks.add(name)
        task_lease = controller.local._Lease(task, False)
        try:
            resources = controller.process.resources
            host = resources.HostResourceBudget(budget.task_process_budget.max_job_commit_bytes, budget.commit_reserve_bytes, (
                resources.DirectoryDemand('archive', str(task), budget.archive_bytes_per_task, budget.disk_reserve_bytes),
                resources.DirectoryDemand('scratch', str(task/'scratch'), budget.scratch_bytes_per_task, budget.disk_reserve_bytes)))
            controller_pin = controller.controller_identity(task, request, budget=budget.task_process_budget,
                host_budget=host, environment=environment, max_record_bytes=budget.max_record_bytes)
            result = read(task/'result.json')
            receipt = read(task/'receipt_non_authoritative.json')
            if (type(result) is not dict or set(result) != {'schema', 'controller_identity', 'status', 'receipt_sha256',
                    'inspection', 'observation', 'formal_result', 'whole_task_resources_verified',
                    'numerical_evidence_verified', 'executable_resume_available'}
                    or result['schema'] != controller.SCHEMA
                    or type(receipt) is not dict or set(receipt) != {'schema', 'request_sha256', 'implementation_identity',
                    'store_binding_identity', 'result_identity', 'reported_status', 'inspection', 'formal_result',
                    'whole_task_resources_verified'}):
                raise ValueError('exact controller/receipt inventory required')
            if (result.get('controller_identity') != controller_pin or result.get('status') != 'returned_unverified'
                    or result.get('receipt_sha256') != retained[task/'receipt_non_authoritative.json'][1]
                    or result.get('formal_result') is not False or result.get('whole_task_resources_verified') is not False
                    or result.get('numerical_evidence_verified') is not False or result.get('executable_resume_available') is not False):
                raise ValueError('controller result declaration mismatch')
            observation = result['observation']
            if (type(observation) is not dict or set(observation) != {f.name for f in fields(controller.process.TaskProcessObservation)}
                    or type(observation['pid']) is not int or observation['pid'] <= 0
                    or type(observation['creation_filetime']) is not int or observation['creation_filetime'] <= 0
                    or observation['job_commit_limits_configured'] is not True
                    or any(observation[k] is not False for k in ('hard_disk_quota_enforced',
                        'whole_task_resources_verified', 'numerical_evidence_verified', 'formal_result'))):
                raise ValueError('process observation inventory/authority mismatch')
            for metric, ceiling in (('job_peak_process_commit_bytes', budget.task_process_budget.max_process_commit_bytes),
                                  ('job_peak_total_commit_bytes', budget.task_process_budget.max_job_commit_bytes)):
                if type(observation[metric]) is not int or not 0 <= observation[metric] <= ceiling:
                    raise ValueError('process peak exceeds declared limit')
            if (type(observation['runtime_samples']) is not int or observation['runtime_samples'] < 0
                    or type(observation['elapsed_seconds']) not in (int, float)
                    or not isfinite(observation['elapsed_seconds']) or observation['elapsed_seconds'] < 0):
                raise ValueError('invalid process time/sample observation')
            if (observation.get('whole_job_quiescent') is not True or observation.get('reason') != 'child_exited'
                    or type(observation.get('exit_code')) is not int or observation['exit_code'] != 0
                    or observation['last_resource_errors'] != [] or observation['observation_error_type'] is not None
                    or observation['stop_markers'] != ['direct_child_exit_observed']):
                raise ValueError('completed phase lacks recorded quiet normal exit')
            if (receipt.get('schema') != controller.worker.SCHEMA
                    or receipt.get('request_sha256') != sha256(controller.worker.export_request(request)).hexdigest()
                    or receipt.get('implementation_identity') != controller.worker.implementation_identity()
                    or receipt.get('formal_result') is not False or receipt.get('whole_task_resources_verified') is not False):
                raise ValueError('worker receipt request/implementation mismatch')
            raw_request = controller.worker.export_request(request)
            packet_pin = sha256(raw_request).hexdigest()
            worker_pin = controller.worker.implementation_identity()
            argv = [str(Path(sys.executable).resolve()), '-I', '-B', str(Path(controller.worker.__file__).resolve()),
                '--request-path', str(task/'request.json'), '--expected-request-sha256', packet_pin,
                '--store-root', str(task/'selector_non_authoritative'), '--receipt-path', str(task/'receipt_non_authoritative.json'),
                '--max-request-bytes', str(controller.LIMIT), '--max-record-bytes', str(budget.max_record_bytes),
                '--expected-implementation-identity', worker_pin]
            scratch = task/'scratch'
            process_pin = controller.process.task_process_identity(argv, cwd=scratch,
                environment=dict(environment, TEMP=str(scratch), TMP=str(scratch)), budget=budget.task_process_budget,
                host_budget=host, expected_host_identity=resources.resource_identity(host))
            if observation['process_identity'] != process_pin:
                raise ValueError('process observation differs from independent command identity')
            if not _same(read(task/'request.json'), controller.worker.store._decoded(raw_request)):
                raise ValueError('task request packet mismatch')
            if not _same(read(task/'intent.json'), dict(schema=controller.SCHEMA, controller_identity=controller_pin,
                    request_sha256=packet_pin, implementation_identity=worker_pin, process_identity=process_pin,
                    budget=asdict(budget.task_process_budget), host_budget=asdict(host),
                    planned_solver_calls=request.budget.max_solver_calls,
                    reserved_solver_seconds=request.budget.max_total_solver_seconds, formal_result=False)):
                raise ValueError('task intent differs from independently derived reservation')
            if (not _same(read(task/'observation.json'), observation)
                    or not _same(read(task/'launch.json'), dict(process_identity=process_pin,
                        pid=observation['pid'], creation_filetime=observation['creation_filetime']))):
                raise ValueError('task launch/observation crosslink mismatch')
            archive = task/'selector_non_authoritative'
            archive_lease = controller.local._Lease(archive, False)
            try:
                path = archive/'selector.sqlite3'
                file_pin = episode._file_pin(path)
                inspection, record = controller.worker.store._read(path, receipt['store_binding_identity'], budget.max_record_bytes)
                if record is None or record['result_identity'] != receipt['result_identity']:
                    raise ValueError('selector result binding mismatch')
                if not _same(inspection, receipt['inspection']) or not _same(inspection, result['inspection']):
                    raise ValueError('selector inspection mismatch')
                raw = controller.worker.store._bytes(record)
                retained[path] = file_pin
                replay_pin = tx.replay.implementation_identity(request)
                files = {str(p.relative_to(lease.root)): dict(identity=retained[p][0], sha256=retained[p][1])
                    for p in (task/'result.json', task/'receipt_non_authoritative.json', path)}
                expected = dict(role=role, status='returned_unverified', relative_root=name,
                    controller_identity=controller_pin, receipt_sha256=result['receipt_sha256'],
                    store_binding_identity=receipt['store_binding_identity'], result_identity=receipt['result_identity'],
                    record_sha256=sha256(raw).hexdigest(), replay_implementation_identity=replay_pin,
                    process_identity=observation['process_identity'], files=files)
                if not _same(saved, expected):
                    raise ValueError('phase evidence differs from independently collected artifacts')
                archived = controller.worker.store._fields(record['encoded_result'], tx.replay.scale.ScaleSelectionResult)
                if archived['status'] != receipt['reported_status']:
                    raise ValueError('receipt reported outcome mismatch')
                if archived['status'] == 'selected': selected_phases += 1
                else: unresolved_phases += 1
                archive_lease.check()
                task_lease.check()
                check()
                return raw, dict(expected_sha256=sha256(raw).hexdigest(), expected_replay_identity=replay_pin,
                                 max_record_bytes=budget.max_record_bytes)
            finally:
                archive_lease.close()
        finally:
            task_lease.close()
    try:
        header = read(lease.root/'header.json', expected_header_sha256)
        expected = dict(schema=episode.SCHEMA, implementation=impl,
            inputs=tx.legacy._plain((request0, setups, window)), budget=asdict(budget), resource_plan=asdict(resource_plan),
            environment_sha256=sha256(controller.worker.store._bytes(environment)).hexdigest(), formal_result=False)
        if not _same(header, expected):
            raise ValueError('header differs from independent inputs')
        if ({p.name for p in lease.root.glob('*.intent.json')} != {f'{i:06d}.intent.json' for i in range(n)}
                or {p.name for p in lease.root.glob('*.result.json')} != {f'{i:06d}.result.json' for i in range(m)}):
            raise ValueError('noncontiguous or unexpected hour inventory')
        publication, cursors, previous_resource = None, None, None
        for index in range(n):
            intent = read(lease.root/f'{index:06d}.intent.json', expected_intent_sha256s[index])
            if not _same(intent, dict(sequence=index, previous=None if publication is None else publication.identity,
                    reserved_solver_calls=(index+1)*calls, reserved_solver_seconds=(index+1)*seconds)):
                raise ValueError('hour intent predecessor/reservation mismatch')
            if index == m: break
            saved = read(lease.root/f'{index:06d}.result.json', expected_result_sha256s[index])
            episode.resources.validate_observation(saved['resource_observation'], budget, previous_resource)
            previous_resource = saved['resource_observation']
            phases = saved['phase_evidence']
            if type(phases) is not list or len(phases) != 5:
                raise ValueError('complete canonical five-phase inventory required')
            hour = window[index]
            before = request0.before if publication is None else publication.reference_result.next_state
            request = replace(request0, info=hour.info, disclosure=hour.disclosure, before=before,
                budget=replace(request0.budget, source_hour=hour.info.current.source_hour),
                expected_identity=tx.replay.scale.reference.reference_input_identity(hour.info, hour.disclosure, before))
            data, pins = phase(index, 'reference', request, phases[0])
            pub = tx.publish_common_record(data, request, hour.source_hour, hour.mapping, hour.source_audit,
                previous=publication, limits=hour.limits, due_hour=hour.due_hour,
                available_flexibility=hour.available_flexibility, **pins)
            incoming = cursors or tuple(tx.initialize_arm(pub, a.business, a.grid) for a in setups)
            next_cursors, results = [], []
            for i, (cursor, setup) in enumerate(zip(incoming, setups)):
                role = 'actual:'+str(i)
                if cursor.halted:
                    if phases[i+1] != dict(role=role, status='skipped_previously_halted'):
                        raise ValueError('halted arm phase mismatch')
                    next_cursors.append(cursor)
                    results.append(dict(status='previously_halted', arm_id=tx.ARMS[i]))
                    continue
                proposal = tx.prepare_arm(cursor, pub, selector=setup.selector, solver_specification=setup.specification,
                    budget=replace(setup.budget, source_hour=hour.info.current.source_hour))
                if proposal.dispatch_request is None:
                    if phases[i+1] != dict(role=role, status='skipped_business_rejected'):
                        raise ValueError('business rejection phase mismatch')
                    result = tx.finish_arm(proposal)
                else:
                    data, pins = phase(index, role, proposal.dispatch_request, phases[i+1])
                    result = tx.finish_arm(proposal, data, **pins)
                next_cursors.append(result['cursor'])
                results.append(result)
            expected = dict(schema=episode.SCHEMA, sequence=index, phase_evidence=phases,
                resource_observation=saved['resource_observation'],
                publication=tx.legacy._plain(pub), arms=tx.legacy._plain(tuple(next_cursors)),
                results=tx.legacy._plain(tuple(results)), reserved_solver_calls=(index+1)*calls,
                reserved_solver_seconds=(index+1)*seconds,
                status='observation_window_consumed' if index+1 == len(window) else 'advanced',
                formal_result=False, whole_task_resources_verified=False, executable_resume_available=False)
            if not _same(saved, expected):
                raise ValueError('hour cursor/result differs from independent replay')
            publication, cursors = pub, tuple(next_cursors)
        actual_tasks = {p.name for p in lease.root.iterdir() if p.is_dir()}
        pending_tasks = ({f'{m:06d}_reference_non_authoritative'} |
            {f'{m:06d}_actual_{i}_non_authoritative' for i in range(4)}) if n > m else set()
        if not consumed_tasks <= actual_tasks or not actual_tasks <= consumed_tasks | pending_tasks:
            raise ValueError('undeclared or missing task directory inventory')
        expected_names = {'execution.lock', 'header.json'} | actual_tasks
        expected_names |= {f'{i:06d}.intent.json' for i in range(n)}
        expected_names |= {f'{i:06d}.result.json' for i in range(m)}
        if {p.name for p in lease.root.iterdir()} != expected_names:
            raise ValueError('unexpected episode root entry inventory')
        check()
        return dict(schema=SCHEMA, status='pending_unknown' if n > m else 'reproduced_hour_prefix',
            completed_hours=m, planned_hours=len(window), pending_intent=n > m,
            reserved_solver_calls=n*calls, reserved_solver_seconds=n*seconds,
            selected_phase_chains_replayed=selected_phases, unresolved_phase_records=unresolved_phases,
            unresolved_numerical_details_replayed=False, observation_window_consumed=m == len(window),
            solver_calls_by_auditor=0, native_execution_authenticated=False, whole_job_quiescence_verified=False,
            complete_service_certified=False, formal_result=False, executable_resume_available=False)
    finally:
        lease.close()
