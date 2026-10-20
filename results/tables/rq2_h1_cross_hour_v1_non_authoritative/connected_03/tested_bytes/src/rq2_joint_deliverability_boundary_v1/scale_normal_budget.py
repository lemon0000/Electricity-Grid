"""Normal numerical allocation within a complete caller-declared resource plan.

The normal kernel allocation excludes source preparation, archive and replay.
It is not a whole-task resource certificate or execution permission.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path

from . import execution_resource_contract as resources, execution_workload as workload
from .identity_stream_ordered import normal_input_identity, digest


def implementation_identity():
    return tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest())
                 for m in (resources, workload)) + (("scale_normal_budget", sha256(Path(__file__).read_bytes()).hexdigest()),)


@dataclass(frozen=True)
class NormalResourcePlan:
    normals: tuple
    episodes: tuple
    envelopes: tuple
    serial_budget: resources.SerialResourceBudget


@dataclass(frozen=True)
class SingleNormalResourcePlan:
    """One normal diagnostic, with no dependent episode or reuse declaration."""
    normal: workload.NormalWork
    envelope: resources.TaskEnvelope
    serial_budget: resources.SerialResourceBudget


def check_single_normal_plan(plan):
    if (type(plan) is not SingleNormalResourcePlan
            or type(plan.normal) is not workload.NormalWork
            or type(plan.envelope) is not resources.TaskEnvelope
            or type(plan.serial_budget) is not resources.SerialResourceBudget):
        raise ValueError('typed single-normal resource declaration required')
    task, envelope, serial = plan.normal, plan.envelope, plan.serial_budget
    workload._validate(task)
    workload._positive(task.seconds_per_solve)
    resources._validate_positive_fields(envelope, ('task_id',))
    resources._validate_positive_fields(serial)
    if type(envelope.task_id) is not str or envelope.task_id != task.task_id:
        raise ValueError('single normal envelope task ID differs')
    wall = envelope.max_wall_seconds+serial.controller_seconds
    commit = envelope.max_job_commit_bytes+serial.supervisor_additional_commit_bytes+serial.commit_reserve_bytes
    disk = envelope.archive_bytes+envelope.scratch_bytes+serial.disk_reserve_bytes
    errors = tuple(name for required, maximum, name in (
        (task.seconds_per_solve+envelope.non_solver_seconds, envelope.max_wall_seconds, 'task_wall_reservation_shortfall'),
        (envelope.max_threads, serial.max_threads, 'thread_cap_exceeds_plan'),
        (wall, serial.max_total_wall_seconds, 'total_wall_reservation_shortfall'),
        (commit, serial.max_additional_commit_bytes, 'commit_reservation_shortfall'),
        (disk, serial.max_additional_disk_bytes, 'disk_reservation_shortfall'),
    ) if required > maximum)
    return dict(schema='rq2_single_normal_resource_contract_v1', normal=asdict(task),
        envelope=asdict(envelope), serial_budget=asdict(serial),
        normal_tasks=1, episode_tasks=0, solver_calls=1, reserved_solver_seconds=task.seconds_per_solve,
        reserved_total_wall_seconds=wall, required_additional_commit_bytes=commit,
        required_additional_disk_bytes=disk, errors=errors, declaration_consistent=not errors,
        scope='single_normal_diagnostic_only', assumptions=('one_quiescent_job_at_a_time', 'no_scratch_reclamation', 'no_retries'),
        unresolved=('source_validation', 'normal_optimality', 'envelope_measurements', 'host_and_volume_binding',
                    'hard_process_enforcement', 'real_scale_executor_integration', 'scientific_registration'),
        whole_task_resources_verified=False, execution_authorized=False, formal_ready=False)


@dataclass(frozen=True)
class ScaleNormalBudget:
    resource_contract_identity: str
    normal: workload.NormalWork
    envelope: resources.TaskEnvelope
    max_seconds_per_solve: int
    max_threads: int
    max_horizon: int
    max_variables: int
    max_constraints: int
    max_observed_wall_seconds: float
    max_process_peak_working_set_bytes: int
    max_core_evidence_payload_bytes: int

    def __post_init__(self):
        pin = self.resource_contract_identity
        if type(pin) is not str or len(pin) != 64 or any(c not in '0123456789abcdef' for c in pin):
            raise ValueError('complete resource contract SHA256 required')
        if type(self.normal) is not workload.NormalWork or type(self.envelope) is not resources.TaskEnvelope:
            raise ValueError('typed normal task and envelope required')
        workload._validate(self.normal)
        workload._positive(self.normal.seconds_per_solve)
        resources._validate_positive_fields(self.envelope, ('task_id',))
        for name in ('max_seconds_per_solve', 'max_threads', 'max_horizon', 'max_variables',
                     'max_constraints', 'max_process_peak_working_set_bytes', 'max_core_evidence_payload_bytes'):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError('positive integer normal allocation required: '+name)
        wall = self.max_observed_wall_seconds
        if (type(wall) not in (int, float) or not isfinite(wall)
                or not self.max_seconds_per_solve <= wall <= self.envelope.max_wall_seconds):
            raise ValueError('normal wall allocation exceeds task envelope or omits solver reservation')
        if (self.normal.task_id != self.envelope.task_id
                or self.max_seconds_per_solve != self.normal.seconds_per_solve
                or self.max_horizon != len(self.normal.source_hours)
                or self.max_threads != 1 or self.max_threads > self.envelope.max_threads
                or self.max_variables != self.envelope.max_variables
                or self.max_constraints != self.envelope.max_constraints
                or self.max_core_evidence_payload_bytes > self.envelope.archive_bytes):
            raise ValueError('normal allocation differs from task declaration')
        # Working set and commit are different resources; no implication between
        # the declared working-set cap and the Job commit cap is asserted here.


def budget_for_task(plan, *, task_id, max_observed_wall_seconds,
                    max_process_peak_working_set_bytes, max_core_evidence_payload_bytes):
    if type(plan) is SingleNormalResourcePlan:
        report = check_single_normal_plan(plan)
        normals, envelopes = (plan.normal,), (plan.envelope,)
    elif type(plan) is NormalResourcePlan:
        report = resources.check_resource_contract(plan.normals, plan.episodes, plan.envelopes, plan.serial_budget)
        normals, envelopes = plan.normals, plan.envelopes
    else:
        raise ValueError('complete original normal resource plan required')
    if not report['declaration_consistent']:
        raise ValueError('inconsistent original normal resource plan')
    task = next((x for x in normals if x.task_id == task_id), None)
    if task is None:
        raise ValueError('declared normal task required')
    envelope = next(x for x in envelopes if x.task_id == task_id)
    return ScaleNormalBudget(digest(report, implementation_identity()), task, envelope,
        task.seconds_per_solve, 1, len(task.source_hours), envelope.max_variables, envelope.max_constraints,
        max_observed_wall_seconds, max_process_peak_working_set_bytes, max_core_evidence_payload_bytes)


def bind_plan(plan, budget, inputs):
    if type(budget) is not ScaleNormalBudget:
        raise ValueError('typed declared normal budget required')
    expected = budget_for_task(plan, task_id=budget.normal.task_id,
        max_observed_wall_seconds=budget.max_observed_wall_seconds,
        max_process_peak_working_set_bytes=budget.max_process_peak_working_set_bytes,
        max_core_evidence_payload_bytes=budget.max_core_evidence_payload_bytes)
    if expected != budget:
        raise ValueError('normal budget differs from original resource plan')
    task = budget.normal
    if (normal_input_identity(inputs) != task.input_identity
            or inputs.source_hours != task.source_hours or inputs.carry.identity.split != task.split
            or tuple(sorted(g.uid for g in inputs.data.generators)) != task.generator_uids):
        raise ValueError('normal input/hash/hours/split/UID differs from resource declaration')
