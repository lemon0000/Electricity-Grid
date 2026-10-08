"""Whole-episode declarations and sampled limits, not a hard parent Job cap."""
import os
from pathlib import Path
import stat
import time
from dataclasses import dataclass

from . import execution_resource_contract as contract, normal_execution as memory
from . import normal_resources as host
from .scale_selector_controller import LIMIT


@dataclass(frozen=True)
class EpisodeResourcePlan:
    normals: tuple
    episodes: tuple
    envelopes: tuple
    serial_budget: contract.SerialResourceBudget


def bind_plan(plan, budget, request, arms, hours):
    """Recompute declarations against actual inputs; not source certification."""
    from . import scale_selector as scale, common_request_adapter as mapping
    if type(plan) is not EpisodeResourcePlan:
        raise ValueError('typed original resource plan required')
    report = contract.check_resource_contract(plan.normals, plan.episodes, plan.envelopes, plan.serial_budget)
    if not report['declaration_consistent']:
        raise ValueError('inconsistent complete resource plan')
    if (plan.serial_budget.commit_reserve_bytes < budget.commit_reserve_bytes
            or plan.serial_budget.disk_reserve_bytes < budget.disk_reserve_bytes):
        raise ValueError('serial reserves must cover episode runtime reserves')
    task = next((t for t in plan.episodes if t.task_id == request.budget.task_id), None)
    if task is None or task.source_hours != tuple(h.info.current.source_hour for h in hours):
        raise ValueError('actual episode window differs from original resource plan')
    envelope = next(e for e in plan.envelopes if e.task_id == task.task_id)
    if envelope != budget.envelope:
        raise ValueError('episode envelope differs from original resource plan')
    if envelope.max_job_commit_bytes < budget.controller_additional_commit_bytes+budget.task_process_budget.max_job_commit_bytes:
        raise ValueError('episode Job declaration must cover parent plus inner Job')
    for hour in hours:
        audit = hour.source_audit
        if (type(audit) is not mapping.RequestSourceAudit
                or audit.normal_input_identity != task.normal_input_identity
                or audit.split != task.split or audit.source_hour != hour.info.current.source_hour
                or audit.current_visible_identity != hour.info.visible_identity
                or hour.source_hour.split != task.split
                or hour.source_hour.power_source_hour != audit.source_hour
                or hour.source_hour.power_outage_seed != audit.outage_seed
                or tuple(unit.uid for unit in hour.info.network.units) != task.generator_uids):
            raise ValueError('resource plan source/UID/split binding mismatch')
    if len(arms) != 4:
        raise ValueError('four declared roles required')
    for supplied, role in zip((request.budget, *(a.budget for a in arms)),
                              ('reference', 'actual:0', 'actual:1', 'actual:2', 'actual:3'), strict=True):
        expected = scale.budget_for_hour(plan.normals, plan.episodes, plan.envelopes, plan.serial_budget,
            task_id=task.task_id, source_hour=task.source_hours[0], role=role)
        if supplied != expected:
            raise ValueError('selector budget differs from recomputed original resource plan')
    row = next(row for row in report['workload']['rows'] if row['task_id'] == task.task_id)
    if (budget.max_solver_calls != row['solver_calls']
            or budget.max_solver_seconds != row['reserved_solver_seconds']):
        raise ValueError('episode total differs from original resource plan')
    admit(budget, request, arms, hours)


def admit(budget, request, arms, hours):
    envelope = budget.envelope
    if type(envelope) is not contract.TaskEnvelope:
        raise ValueError('existing typed TaskEnvelope required')
    contract._validate_positive_fields(envelope, ('task_id',))
    if envelope.task_id != request.budget.task_id:
        raise ValueError('episode envelope task mismatch')
    phases = 5*len(hours)
    process = budget.task_process_budget
    required_wall = phases*(process.max_elapsed_seconds+process.max_quiescence_seconds)+envelope.non_solver_seconds
    if envelope.max_wall_seconds < required_wall:
        raise ValueError('episode wall cannot cover full phase and parent reservations')
    metadata = (1+2*len(hours))*LIMIT+1
    if (envelope.max_job_commit_bytes < process.max_job_commit_bytes
            or envelope.archive_bytes < phases*budget.archive_bytes_per_task+metadata
            or envelope.scratch_bytes < phases*budget.scratch_bytes_per_task):
        raise ValueError('whole episode envelope cannot cover retained task reservations')
    for b in (request.budget, *(a.budget for a in arms)):
        if b.max_threads > envelope.max_threads or b.max_variables > envelope.max_variables or b.max_constraints > envelope.max_constraints:
            raise ValueError('selector model/thread budget exceeds episode envelope')
    return required_wall


def observe(root, budget, started, *, extra_archive_bytes=0, extra_entries=0):
    envelope = budget.envelope
    def deadline():
        elapsed = time.monotonic()-started
        if elapsed >= envelope.max_wall_seconds:
            raise TimeoutError('episode sampled elapsed limit exceeded')
        return elapsed
    deadline()
    peak = memory._peak_working_set_bytes()
    if peak > budget.max_controller_peak_working_set_bytes:
        raise ValueError('episode controller lifetime working-set limit exceeded')
    totals, count, pending = dict(archive=0, scratch=0), 0, [(Path(root), False)]
    while pending:
        directory, scratch = pending.pop()
        directory = host.local._path(directory)
        with os.scandir(directory) as entries:
            for entry in entries:
                deadline()
                count += 1
                if count+extra_entries > budget.max_tree_entries:
                    raise ValueError('episode tree entry limit exceeded')
                path = Path(entry.path)
                info = path.lstat()
                if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                    raise ValueError('episode tree reparse point refused')
                if stat.S_ISDIR(info.st_mode):
                    pending.append((path, scratch or (directory.parent == Path(root) and path.name == 'scratch')))
                elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                    totals['scratch' if scratch else 'archive'] += info.st_size
                else:
                    raise ValueError('episode tree requires regular single-link files')
    if totals['archive']+extra_archive_bytes > envelope.archive_bytes or totals['scratch'] > envelope.scratch_bytes:
        raise ValueError('episode cumulative logical byte limit exceeded')
    demand = host.HostResourceBudget(budget.controller_additional_commit_bytes, budget.commit_reserve_bytes,
        (host.DirectoryDemand('episode', str(root), max(1, envelope.archive_bytes+envelope.scratch_bytes
             -totals['archive']-totals['scratch']), budget.disk_reserve_bytes),))
    observed = host.observe_headroom(demand, expected_request_identity=host.resource_identity(demand))
    # Demand availability is a conservative sampled admission, not a reservation
    # held by the OS and not a process-private commit measurement.
    if not observed.observed_headroom_sufficient:
        raise ValueError('episode remaining host headroom insufficient')
    return dict(scope='sample_before_publication', elapsed_seconds=deadline(),
        controller_lifetime_peak_working_set_bytes=peak, archive_logical_bytes=totals['archive'],
        scratch_logical_bytes=totals['scratch'], tree_entries=count,
        system_commit_available_bytes=observed.commit.available_bytes,
        hard_parent_wall_limit=False, hard_parent_commit_limit=False, hard_disk_quota=False,
        whole_task_resources_verified=False)


def validate_observation(observation, budget, previous=None):
    expected = {'scope', 'elapsed_seconds', 'controller_lifetime_peak_working_set_bytes',
        'archive_logical_bytes', 'scratch_logical_bytes', 'tree_entries', 'system_commit_available_bytes',
        'hard_parent_wall_limit', 'hard_parent_commit_limit', 'hard_disk_quota', 'whole_task_resources_verified'}
    from math import isfinite
    if type(observation) is not dict or set(observation) != expected or observation['scope'] != 'sample_before_publication':
        raise ValueError('exact episode resource observation required')
    elapsed = observation['elapsed_seconds']
    if type(elapsed) not in (int, float) or not isfinite(elapsed) or not 0 <= elapsed < budget.envelope.max_wall_seconds:
        raise ValueError('episode elapsed observation outside envelope')
    for key, ceiling in (('controller_lifetime_peak_working_set_bytes', budget.max_controller_peak_working_set_bytes),
                         ('archive_logical_bytes', budget.envelope.archive_bytes),
                         ('scratch_logical_bytes', budget.envelope.scratch_bytes), ('tree_entries', budget.max_tree_entries)):
        if type(observation[key]) is not int or not 0 <= observation[key] <= ceiling:
            raise ValueError('episode resource observation outside envelope: '+key)
    if (type(observation['system_commit_available_bytes']) is not int
            or observation['system_commit_available_bytes'] < budget.commit_reserve_bytes+budget.controller_additional_commit_bytes
            or any(observation[k] is not False for k in ('hard_parent_wall_limit', 'hard_parent_commit_limit',
                                                       'hard_disk_quota', 'whole_task_resources_verified'))):
        raise ValueError('episode resource observation authority/headroom mismatch')
    if previous is not None:
        validate_observation(previous, budget)
        for key in ('elapsed_seconds', 'controller_lifetime_peak_working_set_bytes',
                    'archive_logical_bytes', 'scratch_logical_bytes', 'tree_entries'):
            if observation[key] < previous[key]:
                raise ValueError('episode cumulative resource observation decreased: '+key)
