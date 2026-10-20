"""Declared serial workload accounting; no solver, admission or execution authority.

Each episode is one complete four-arm evaluation, not a capacity search or cell.
Reusing a normal task ID declares a dependency; it does not certify reuse validity.
"""
from dataclasses import asdict, dataclass
from fractions import Fraction


@dataclass(frozen=True)
class NormalWork:
    task_id: str
    split: str
    input_identity: str
    generator_uids: tuple[str, ...]
    source_hours: tuple[int, ...]
    seconds_per_solve: int


@dataclass(frozen=True)
class EpisodeWork:
    task_id: str
    split: str
    normal_task_id: str
    normal_input_identity: str
    generator_uids: tuple[str, ...]
    source_hours: tuple[int, ...]
    reference_seconds: int
    # Canonical order: network-only, CFE-only, joint-correct, joint-B6.
    actual_seconds: tuple[int, int, int, int]


def _positive(value):
    if type(value) is not int or value <= 0:
        raise ValueError('positive integer seconds required')


def _validate(task):
    if type(task.task_id) is not str or not task.task_id.strip():
        raise ValueError('explicit task ID required')
    if task.split not in ('training', 'holdout'):
        raise ValueError('explicit training or holdout split required')
    uids, hours = task.generator_uids, task.source_hours
    if (type(uids) is not tuple or not uids
            or any(type(x) is not str or not x for x in uids)
            or uids != tuple(sorted(set(uids)))):
        raise ValueError('sorted unique complete declared UID inventory required')
    if (type(hours) is not tuple or not hours
            or any(type(x) is not int or x < 0 for x in hours)
            or any(b != a+1 for a, b in zip(hours, hours[1:]))):
        raise ValueError('explicit contiguous source-hour inventory required')
    pin = task.input_identity if type(task) is NormalWork else task.normal_input_identity
    if type(pin) is not str or len(pin) != 64 or any(c not in '0123456789abcdef' for c in pin):
        raise ValueError('normal input SHA256 required')


def summarize_workload(normals, episodes):
    """Count every declared task once; all paths reserved even if execution stops.

    Integer seconds are declaration units, not measurements. No retry, warm-start
    generation, parallel scheduling or unlisted capacity-search step is inferred.
    Input pins are checked for agreement only, not against source files.
    """
    if (type(normals) is not tuple or not normals or type(episodes) is not tuple or not episodes
            or any(type(x) is not NormalWork for x in normals)
            or any(type(x) is not EpisodeWork for x in episodes)):
        raise ValueError('explicit nonempty typed normal and episode inventories required')
    for task in normals+episodes:
        _validate(task)
    ids = [task.task_id for task in normals+episodes]
    if len(set(ids)) != len(ids):
        raise ValueError('globally unique task IDs required')
    by_id = {task.task_id: task for task in normals}
    used, rows = set(), []
    for task in normals:
        _positive(task.seconds_per_solve)
        rows.append(dict(task_id=task.task_id, split=task.split, kind='normal',
                         solver_calls=1, reserved_solver_seconds=task.seconds_per_solve))
    for task in episodes:
        if type(task.normal_task_id) is not str or task.normal_task_id not in by_id:
            raise ValueError('episode requires a declared normal dependency')
        normal = by_id[task.normal_task_id]
        if (task.split != normal.split or task.normal_input_identity != normal.input_identity
                or task.generator_uids != normal.generator_uids):
            raise ValueError('normal dependency split, input or UID mismatch')
        if not set(task.source_hours).issubset(normal.source_hours):
            raise ValueError('episode hours outside declared normal window')
        _positive(task.reference_seconds)
        if type(task.actual_seconds) is not tuple or len(task.actual_seconds) != 4:
            raise ValueError('all four canonical arm budgets required')
        for seconds in task.actual_seconds:
            _positive(seconds)
        n, h = len(task.generator_uids), len(task.source_hours)
        reference_calls, actual_calls = h*(n+2), (h*(n+1),)*4
        calls = reference_calls+sum(actual_calls)
        seconds = reference_calls*task.reference_seconds+sum(
            count*limit for count, limit in zip(actual_calls, task.actual_seconds))
        rows.append(dict(task_id=task.task_id, split=task.split, kind='episode',
                         normal_task_id=normal.task_id, reference_calls=reference_calls,
                         actual_calls=actual_calls, solver_calls=calls,
                         reserved_solver_seconds=seconds))
        used.add(normal.task_id)
    if used != set(by_id):
        raise ValueError('unreferenced normal task in complete episode inventory')
    total = sum(row['reserved_solver_seconds'] for row in rows)
    return dict(schema='rq2_declared_execution_workload_v1', rows=tuple(rows),
                normal_declarations=tuple(asdict(task) for task in normals),
                episode_declarations=tuple(asdict(task) for task in episodes),
                normal_tasks=len(normals), episode_tasks=len(episodes),
                solver_calls=sum(row['solver_calls'] for row in rows),
                reserved_solver_seconds=total, reserved_solver_hours=str(Fraction(total, 3600)),
                scope='caller_declared_inventory_only',
                unresolved=('inventory_completeness', 'source_and_reuse_validation',
                            'normal_optimality', 'wall_memory_disk_budgets',
                            'runtime_capacity', 'scientific_registration'),
                execution_authorized=False, formal_ready=False)
