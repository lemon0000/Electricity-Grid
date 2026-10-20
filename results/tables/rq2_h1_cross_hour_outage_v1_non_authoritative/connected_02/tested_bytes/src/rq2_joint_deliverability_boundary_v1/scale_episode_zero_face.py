"""One-shot development episode owner with supervised selector tasks.

Completed hour files are retained observations, not executable checkpoints.
"""
from copy import deepcopy
from dataclasses import dataclass, fields, replace, asdict
from hashlib import sha256
from pathlib import Path
from threading import Lock
import time

from . import scale_hourly_zero_face_transaction as tx, scale_selector_zero_face_controller as controller
from . import scale_episode_resources as resources
from . import grid_evidence_replay as native_replay

SCHEMA = 'draft_supervised_mixed_selector_episode_v1'


@dataclass(frozen=True)
class ArmSetup:
    business: object
    grid: object
    selector: object
    specification: object
    budget: object


@dataclass(frozen=True)
class HourInput:
    info: object
    disclosure: object
    source_hour: object
    source_audit: object
    mapping: object
    limits: object
    due_hour: int | None
    available_flexibility: float


@dataclass(frozen=True)
class EpisodeBudget:
    max_solver_calls: int
    max_solver_seconds: int
    task_process_budget: object
    archive_bytes_per_task: int
    scratch_bytes_per_task: int
    commit_reserve_bytes: int
    disk_reserve_bytes: int
    max_record_bytes: int
    envelope: object
    max_controller_peak_working_set_bytes: int
    controller_additional_commit_bytes: int
    max_tree_entries: int

    def __post_init__(self):
        if type(self.task_process_budget) is not controller.process.TaskProcessBudget:
            raise ValueError('typed task process budget required')
        self.task_process_budget.__post_init__()
        for f in fields(self):
            if f.name not in ('task_process_budget', 'envelope') and (type(getattr(self, f.name)) is not int or getattr(self, f.name) <= 0):
                raise ValueError('explicit positive episode budget required')
        if type(self.envelope) is not resources.contract.TaskEnvelope:
            raise ValueError('typed complete task envelope required')
        resources.contract._validate_positive_fields(self.envelope, ('task_id',))
        if self.max_record_bytes > controller.LIMIT:
            raise ValueError('record exceeds controller limit')


def _implementation():
    root = Path(__file__).resolve().parents[2]
    return tx.legacy._identity(SCHEMA, tx._implementation(), controller.worker.implementation_identity(),
        tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in (resources, resources.memory)),
        tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in
              (controller.process, controller.process.process, controller.process.resources, controller.local)),
        tuple((name, sha256((root/name).read_bytes()).hexdigest()) for name in native_replay.DEPENDENCIES),
        sha256(Path(controller.supervision.__file__).read_bytes()).hexdigest(),
        sha256(Path(controller.__file__).read_bytes()).hexdigest(),
        sha256(Path(__file__).read_bytes()).hexdigest())


def _file_pin(path):
    before = controller.local._file_identity(path)
    digest = sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024**2): digest.update(chunk)
    if controller.local._file_identity(path) != before:
        raise ValueError('consumed task artifact replaced')
    return before, digest.hexdigest()


def _fairness(arms):
    if type(arms) is not tuple or len(arms) != 4 or any(type(a) is not ArmSetup for a in arms):
        raise ValueError('four typed arm setups required')
    if tuple(a.business.spec.arm_id for a in arms) != tx.ARMS:
        raise ValueError('canonical four distinct business arms required')
    first = arms[0]
    for index, arm in enumerate(arms):
        arm.business.__post_init__()
        if arm.business.records or type(arm.grid) is not tx.scale.actual.ActualDispatchOrigin:
            raise ValueError('unused business and actual origins required')
        for f in fields(first.business.spec):
            if f.name not in ('arm_id', 'committed_capacity', 'capacity_declaration_id'):
                if getattr(first.business.spec, f.name) != getattr(arm.business.spec, f.name):
                    raise ValueError('unequal business mechanism: '+f.name)
        track, base = arm.business.initial.tracks[0][1], first.business.initial.tracks[0][1]
        if (track.physical != base.physical or track.ledger.accounting_period_id != base.ledger.accounting_period_id
                or tx.scale.actual._physical(arm.grid) != tx.scale.actual._physical(first.grid)
                or arm.selector != first.selector or arm.specification != first.specification
                or arm.budget.role != 'actual:'+str(index)
                or replace(arm.budget, role='actual:0') != first.budget):
            raise ValueError('unequal origin/actual policy/reservation or wrong arm role')
        if arm.grid.selector_policy_identity != tx.scale.policy_identity(arm.selector, arm.specification, arm.budget):
            raise ValueError('actual origin policy mismatch')


class DevelopmentMixedSelectorEpisode:
    def __init__(self, root, reference_request, arms, hours, *, budget, environment, resource_plan):
        self._started = time.monotonic()
        self._lease = None
        self._closed, self._poisoned = False, False
        self._guard = Lock()
        self._reference, self._arms, self._hours, self._budget, self._environment = deepcopy((
            reference_request, arms, hours, budget, environment))
        self._resource_plan = deepcopy(resource_plan)
        if type(self._environment) is not dict:
            raise ValueError('explicit private task environment required')
        controller.process.process._environment_block(self._environment)
        _fairness(self._arms)
        if type(budget) is not EpisodeBudget:
            raise ValueError('typed episode budget required')
        budget.__post_init__()
        if type(hours) is not tuple or not hours or any(type(h) is not HourInput for h in hours):
            raise ValueError('complete nonempty declared hour window required')
        if (type(reference_request) is not controller.worker.store.MixedSelectorRequest
                or type(reference_request.before) is not tx.scale.reference.ReferenceGridOrigin
                or reference_request.budget.role != 'reference' or reference_request.power is not None):
            raise ValueError('reference request required')
        controller.worker.decode_request(controller.worker.export_request(reference_request))
        start = reference_request.budget.source_hour
        if tuple(h.info.current.source_hour for h in hours) != tuple(range(start, start+len(hours))):
            raise ValueError('contiguous declared hour window required')
        if (reference_request.info != hours[0].info or reference_request.disclosure != hours[0].disclosure
                or any(a.budget.source_hour != start for a in arms)):
            raise ValueError('initial request/setup differs from declared window')
        budgets = (reference_request.budget, *(a.budget for a in arms))
        for b in budgets:
            b.__post_init__()
            if (b.generator_uids != reference_request.budget.generator_uids
                    or b.task_id != reference_request.budget.task_id
                    or b.resource_contract_identity != reference_request.budget.resource_contract_identity
                    or b.max_total_solver_seconds > budget.task_process_budget.max_elapsed_seconds):
                raise ValueError('inconsistent episode task/resource/UID or phase reservation')
        self._calls = sum(b.max_solver_calls for b in budgets)
        self._seconds = sum(b.max_total_solver_seconds for b in budgets)
        if self._calls*len(hours) > budget.max_solver_calls or self._seconds*len(hours) > budget.max_solver_seconds:
            raise ValueError('complete four-arm window exceeds episode reservation')
        resources.admit(budget, reference_request, arms, hours)
        resources.bind_plan(self._resource_plan, self._budget, self._reference, self._arms, self._hours)
        self._index, self._publication, self._cursors = 0, None, None
        self._retained = {}
        self._artifacts = {}
        self._implementation = _implementation()
        self._header = dict(schema=SCHEMA, implementation=self._implementation,
            inputs=tx.legacy._plain((self._reference, self._arms, self._hours)),
            budget=asdict(budget), resource_plan=asdict(self._resource_plan),
            environment_sha256=sha256(controller.worker.store._bytes(self._environment)).hexdigest(),
            formal_result=False)
        lease = object.__new__(controller.local._Lease)
        try:
            controller.local._Lease.__init__(lease, root, True)
            self._lease = lease
            self._write('header.json', self._header)
        except BaseException:
            if getattr(lease, 'stream', None) is not None: lease.close()
            raise

    def _write(self, name, body):
        path = self._lease.root/name
        resources.observe(self._lease.root, self._budget, self._started,
            extra_archive_bytes=len(controller.worker.store._bytes(body)), extra_entries=1)
        self._retained[path] = controller._write(path, body)

    def _check(self, in_progress=False):
        if self._closed or (self._poisoned and not in_progress):
            raise ValueError('closed or interrupted episode cannot advance')
        self._lease.check()
        if _implementation() != self._implementation:
            raise ValueError('episode implementation drift')
        if sha256(controller.worker.store._bytes(self._environment)).hexdigest() != self._header['environment_sha256']:
            raise ValueError('episode environment drift')
        for path, (identity, digest) in self._retained.items():
            if sha256(controller.worker.store._bytes(controller._read(path, identity))).hexdigest() != digest:
                raise ValueError('episode journal drift')
        for path, pin in self._artifacts.items():
            if _file_pin(path) != pin:
                raise ValueError('consumed task artifact drift')
        observation = resources.observe(self._lease.root, self._budget, self._started)
        resources.validate_observation(observation, self._budget, getattr(self, '_last_resource_observation', None))
        self._last_resource_observation = observation

    def _task(self, name, request):
        self._check(in_progress=True)
        required = self._budget.task_process_budget.max_elapsed_seconds+self._budget.task_process_budget.max_quiescence_seconds
        if self._budget.envelope.max_wall_seconds-(time.monotonic()-self._started) < required:
            raise TimeoutError('episode remaining wall cannot cover next full task')
        root = self._lease.root/name
        resources = controller.process.resources
        b = self._budget
        host = resources.HostResourceBudget(b.task_process_budget.max_job_commit_bytes, b.commit_reserve_bytes, (
            resources.DirectoryDemand('archive', str(root), b.archive_bytes_per_task, b.disk_reserve_bytes),
            resources.DirectoryDemand('scratch', str(root/'scratch'), b.scratch_bytes_per_task, b.disk_reserve_bytes)))
        args = dict(budget=b.task_process_budget, host_budget=host, environment=self._environment,
                    max_record_bytes=b.max_record_bytes)
        pin = controller.controller_identity(root, request, **args)
        observed = controller.supervise_selector(root, request, expected_controller_identity=pin, **args)
        task_lease = controller.local._Lease(root, False)
        try:
            return self._collect_task(root, name, request, pin, observed, task_lease)
        finally:
            task_lease.close()

    def _collect_task(self, root, name, request, pin, observed, task_lease):
        b = self._budget
        receipt = controller._read(root/'receipt_non_authoritative.json')
        if sha256(controller.worker.store._bytes(receipt)).hexdigest() != observed['receipt_sha256']:
            raise ValueError('task receipt changed after supervision')
        archive = root/'selector_non_authoritative'
        lease = controller.local._Lease(archive, False)
        try:
            path = archive/'selector.sqlite3'
            file_identity = controller.local._file_identity(path)
            _, record = controller.worker.store._read(path, receipt['store_binding_identity'], b.max_record_bytes)
            if record is None or record['result_identity'] != receipt['result_identity']:
                raise ValueError('task record changed after supervision')
            lease.check()
            if controller.local._file_identity(path) != file_identity:
                raise ValueError('task database replaced')
            raw = controller.worker.store._bytes(record)
            files = {}
            for file in (root/'result.json', root/'receipt_non_authoritative.json', path):
                file_pin = _file_pin(file)
                self._artifacts[file] = file_pin
                files[str(file.relative_to(self._lease.root))] = dict(identity=file_pin[0], sha256=file_pin[1])
            if (self._artifacts[root/'receipt_non_authoritative.json'][1] != observed['receipt_sha256']
                    or self._artifacts[root/'result.json'][1] != sha256(controller.worker.store._bytes(observed)).hexdigest()
                    or controller.worker.store._bytes(controller._read(root/'result.json')) != controller.worker.store._bytes(observed)):
                raise ValueError('consumed task result/receipt crosslink changed')
            _, reread = controller.worker.store._read(path, receipt['store_binding_identity'], b.max_record_bytes)
            if controller.worker.store._bytes(reread) != raw:
                raise ValueError('consumed task record crosslink changed')
            lease.check()
            task_lease.check()
            replay_pin = tx.replay.implementation_identity()
            evidence = dict(role=request.budget.role, status='returned_unverified', relative_root=name,
                controller_identity=pin, receipt_sha256=observed['receipt_sha256'],
                store_binding_identity=receipt['store_binding_identity'], result_identity=receipt['result_identity'],
                record_sha256=sha256(raw).hexdigest(), replay_implementation_identity=replay_pin,
                process_identity=observed['observation']['process_identity'], files=files)
            self._check(in_progress=True)
            return raw, dict(expected_sha256=sha256(raw).hexdigest(),
                expected_binding_identity=receipt['store_binding_identity'],
                expected_replay_identity=replay_pin, max_record_bytes=b.max_record_bytes), evidence
        finally:
            lease.close()

    def advance(self):
        if not self._guard.acquire(False):
            raise ValueError('episode already advancing')
        try:
            self._check()
            if self._index >= len(self._hours):
                raise ValueError('declared window already consumed')
            index, hour = self._index, self._hours[self._index]
            # The full four-arm reservation is charged even if an arm is halted.
            self._poisoned = True
            self._write(f'{index:06d}.intent.json', dict(sequence=index,
                previous=None if self._publication is None else self._publication.identity,
                reserved_solver_calls=(index+1)*self._calls,
                reserved_solver_seconds=(index+1)*self._seconds))
            before = self._reference.before if self._publication is None else self._publication.reference_result.next_state
            rb = replace(self._reference.budget, source_hour=hour.info.current.source_hour)
            request = replace(self._reference, info=hour.info, disclosure=hour.disclosure, before=before, budget=rb,
                expected_identity=tx.scale.reference.reference_input_identity(hour.info, hour.disclosure, before))
            data, pins, evidence = self._task(f'{index:06d}_reference_non_authoritative', request)
            phases = [evidence]
            pub = tx.publish_common_record(data, request, hour.source_hour, hour.mapping,
                hour.source_audit, previous=self._publication, limits=hour.limits, due_hour=hour.due_hour,
                available_flexibility=hour.available_flexibility, **pins)
            cursors = self._cursors or tuple(tx.initialize_arm(pub, a.business, a.grid) for a in self._arms)
            results, next_cursors = [], []
            for i, (cursor, setup) in enumerate(zip(cursors, self._arms)):
                if cursor.halted:
                    phases.append(dict(role='actual:'+str(i), status='skipped_previously_halted'))
                    results.append(dict(status='previously_halted', arm_id=tx.ARMS[i]))
                    next_cursors.append(cursor)
                    continue
                proposal = tx.prepare_arm(cursor, pub, selector=setup.selector, solver_specification=setup.specification,
                    budget=replace(setup.budget, source_hour=hour.info.current.source_hour))
                if proposal.dispatch_request is None:
                    phases.append(dict(role='actual:'+str(i), status='skipped_business_rejected'))
                    result = tx.finish_arm(proposal)
                else:
                    data, pins, evidence = self._task(f'{index:06d}_actual_{i}_non_authoritative', proposal.dispatch_request)
                    phases.append(evidence)
                    result = tx.finish_arm(proposal, data, **pins)
                results.append(result)
                next_cursors.append(result['cursor'])
            self._check(in_progress=True)
            body = dict(schema=SCHEMA, sequence=index, phase_evidence=phases,
                resource_observation=self._last_resource_observation, publication=tx.legacy._plain(pub),
                arms=tx.legacy._plain(tuple(next_cursors)), results=tx.legacy._plain(tuple(results)),
                reserved_solver_calls=(index+1)*self._calls, reserved_solver_seconds=(index+1)*self._seconds,
                status='observation_window_consumed' if index+1 == len(self._hours) else 'advanced',
                formal_result=False, whole_task_resources_verified=False, executable_resume_available=False)
            self._write(f'{index:06d}.result.json', body)
            self._publication, self._cursors, self._index = pub, tuple(next_cursors), index+1
            self._poisoned = False
            return deepcopy(body)
        finally:
            self._guard.release()

    def close(self):
        if not self._guard.acquire(False):
            raise ValueError('episode already advancing')
        try:
            if self._lease is not None: self._lease.close()
            self._closed = True
        finally:
            self._guard.release()

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
    def __copy__(self): raise TypeError('episode owner cannot be copied')
    def __deepcopy__(self, memo): raise TypeError('episode owner cannot be copied')
    def __reduce_ex__(self, protocol): raise TypeError('episode owner cannot be serialized')
