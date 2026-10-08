"""Controller-owned envelopes around the complete saved-only Job transaction.

The final confirmation tick is live evidence only. No complete-program budget,
native subtraction, resume, or production authority is supplied.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat
import threading
import time
import uuid

from experiments import h1_saved_job_development_v1 as saved

io = saved.io
SCHEMA = 'h1_controller_timing_development_v1'
FLAGS = dict(native_execution_authorized=False, instrumentation_coverage_verified=False,
    observer_overhead_separated=False, component_budget_verified=False,
    resource_admission=False, formal_execution_ready=False, formal_result=False)
JOB_FILES = ('request.json', 'child.json', 'observation.json', 'job_checks.json')


def implementation_identity():
    return io.digest(io.encode([SCHEMA, saved.implementation_identity(),
                               io.digest(Path(__file__).read_bytes())]))


def _tick(value):
    if type(value) is not int or not 0 <= value < 2**63:
        raise ValueError('bounded exact monotonic tick required')
    return value


def _directory(path):
    if path.absolute() != path.resolve(): raise ValueError('canonical timing directory required')
    info = path.stat(follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode): raise ValueError('plain timing directory required')
    return info.st_dev, info.st_ino


def _read(path, pin):
    view = io.read_stable(path, io.META_CAP)
    if io.digest(view[0]) != io.pin(pin): raise ValueError('timing pin differs')
    doc = json.loads(view[0])
    if io.encode(doc) != view[0]: raise ValueError('canonical timing record required')
    return doc, view


def _names(path, cap):
    names = set()
    with os.scandir(path) as entries:
        for entry in entries:
            names.add(entry.name)
            if len(names) > cap: raise ValueError('timing directory entry cap')
    return names


def inspect(root, index, *, expected_binding_sha, expected_intent_sha,
            expected_terminal_sha, expected_implementation):
    """Conditional byte evidence; does not mint a live controller return."""
    if type(index) is not int or not 0 <= index < 192: raise ValueError('hour index required')
    if implementation_identity() != io.pin(expected_implementation): raise ValueError('implementation differs')
    root = Path(root).absolute()
    identity = _directory(root)
    hour = root/f'{index:03d}'
    hour_identity = _directory(hour)
    if _names(hour,2) != {'intent.json', 'terminal.json'}:
        raise ValueError('hour timing topology differs')
    binding, bv = _read(root/'binding.json', expected_binding_sha)
    intent, iv = _read(hour/'intent.json', expected_intent_sha)
    terminal, tv = _read(hour/'terminal.json', expected_terminal_sha)
    if (set(binding) != {'schema','implementation','clock_domain','pid','thread_id',
                        'construction_start_ns',*FLAGS}
            or binding['schema'] != SCHEMA or binding['implementation'] != expected_implementation
            or type(binding['clock_domain']) is not str or len(binding['clock_domain']) != 32
            or any(c not in '0123456789abcdef' for c in binding['clock_domain'])
            or _tick(binding['pid']) == 0 or _tick(binding['thread_id']) == 0
            or any(binding[k] is not False for k in FLAGS)):
        raise ValueError('timing binding differs')
    if (set(intent) != {'schema','binding_sha256','index','start_ns','previous_terminal_sha256',
                       'expected_head','source_identity','raw_declaration_sha256'}
            or intent['schema'] != SCHEMA or intent['binding_sha256'] != expected_binding_sha
            or type(intent['index']) is not int or intent['index'] != index):
        raise ValueError('timing intent differs')
    for name in ('previous_terminal_sha256','expected_head','source_identity','raw_declaration_sha256'):
        io.pin(intent[name])
    if (set(terminal) != {'schema','intent_sha256','end_ns','outcome_head','completed_hours',
                         'status','job_records',*FLAGS}
            or terminal['schema'] != SCHEMA or terminal['intent_sha256'] != expected_intent_sha
            or type(terminal['completed_hours']) is not int or terminal['completed_hours'] != index+1
            or terminal['status'] not in ('ready','complete')
            or any(terminal[k] is not False for k in FLAGS)):
        raise ValueError('timing terminal differs')
    io.pin(terminal['outcome_head'])
    start, end = _tick(intent['start_ns']), _tick(terminal['end_ns'])
    if not _tick(binding['construction_start_ns']) <= start <= end: raise ValueError('clock reversal')
    if type(terminal['job_records']) is not dict or set(terminal['job_records']) != set(JOB_FILES):
        raise ValueError('Job references differ')
    job = root.parent/f'job_{index:03d}_non_authoritative'
    job_identity = _directory(job)
    views = {}
    for name, pin in terminal['job_records'].items():
        view = io.read_stable(job/name, saved.CONTENT_CAP)
        if io.digest(view[0]) != io.pin(pin): raise ValueError('Job evidence pin differs')
        views[job/name] = view
    observation = json.loads(views[job/'observation.json'][0])
    child = json.loads(views[job/'child.json'][0])
    if (observation['whole_job_quiescent'] is not True or type(observation['exit_code']) is not int
            or observation['exit_code'] != 0 or observation['reason'] != 'child_exited'
            or any(observation[k] != child[k] for k in ('pid','creation_filetime','process_identity'))):
        raise ValueError('successful quiescent Job evidence required')
    views.update({root/'binding.json':bv, hour/'intent.json':iv, hour/'terminal.json':tv})
    if (any(io.read_stable(p, saved.CONTENT_CAP if p.parent == job else io.META_CAP) != view
            for p,view in views.items()) or _directory(root) != identity
            or _directory(hour) != hour_identity or _directory(job) != job_identity
            or _names(hour,2) != {'intent.json','terminal.json'}
            or implementation_identity() != expected_implementation):
        raise ValueError('timing evidence changed during inspection')
    return dict(transaction_wall_ns=end-start, outcome_head=terminal['outcome_head'],
        job_records=terminal['job_records'], live_return_observed=False,
        scientific_replay_verified=False, prefix_verified=False, confirmation_tail_ns=None, **FLAGS)


@dataclass(frozen=True)
class Observation:
    transaction_wall_ns: int
    confirmation_tail_ns: int
    total_until_confirmation_ns: int
    terminal_sha256: str
    # Final tick precedes creation/return of this object; it is not persisted.
    final_tick_persisted: bool = False


class TimedSavedController(saved.SavedJobController):
    def __init__(self, *args, clock=time.perf_counter_ns, **kwargs):
        start = _tick(clock())
        self._clock = clock
        self._last_tick = start
        self._timing_owner = os.getpid(), threading.get_ident()
        self._timing_guard = threading.Lock()
        self._timing_poisoned = self._timing_closed = False
        self._timing_index = 0
        self._timing_views = {}
        self._timing_implementation = implementation_identity()
        super().__init__(*args, **kwargs)
        try:
            self.timing_root = self._lease.root/'controller_timing_non_authoritative'
            self.timing_root.mkdir(exist_ok=False)
            self._timing_identity = _directory(self.timing_root)
            self.binding_sha256 = self._save(self.timing_root/'binding.json', dict(schema=SCHEMA,
                implementation=self._timing_implementation, clock_domain=uuid.uuid4().hex,
                pid=self._timing_owner[0], thread_id=self._timing_owner[1],
                construction_start_ns=start, **FLAGS))
            self._timing_previous = self.binding_sha256
            end = self._now(start)
            pin = self._save(self.timing_root/'initialization.json', dict(schema=SCHEMA,
                binding_sha256=self.binding_sha256, end_ns=end))
            self._timing_check()
            final = self._now(end)
            self.initialization_observation = Observation(end-start, final-end, final-start, pin)
        except BaseException:
            self._timing_poisoned = True
            super().close()
            raise

    def _now(self, previous):
        value = _tick(self._clock())
        if value < max(previous,self._last_tick): raise ValueError('controller clock reversal')
        self._last_tick = value
        return value

    def _save(self, path, record):
        pin = io.write_metadata(path, record)
        doc, view = _read(path, pin)
        if not io.same(doc, record): raise ValueError('write differs')
        self._timing_views[path] = view
        return pin

    def _timing_check(self):
        if (self._timing_poisoned or self._timing_closed
                or self._timing_owner != (os.getpid(),threading.get_ident())
                or implementation_identity() != self._timing_implementation
                or _directory(self.timing_root) != self._timing_identity
                or any(io.read_stable(p,io.META_CAP) != v for p,v in self._timing_views.items())):
            raise ValueError('controller timing state/owner/evidence differs')
        expected = {p.name if p.parent == self.timing_root else p.parent.name
                    for p in self._timing_views}
        if _names(self.timing_root,195) != expected:
            raise ValueError('controller timing topology differs')
        for name in expected:
            path = self.timing_root/name
            if path.is_dir() and _names(path,2) != {
                    p.name for p in self._timing_views if p.parent == path}:
                raise ValueError('controller hour topology differs')

    def step_saved_job(self, saved_raws, *, expected_source_identity, expected_head):
        if not self._timing_guard.acquire(blocking=False): raise ValueError('controller timing active')
        try:
            start = self._now(self._last_tick)
            self._timing_check()
            index = self._timing_index
            if index >= 192: raise ValueError('hour cap')
            io.pin(expected_source_identity); io.pin(expected_head)
            if type(saved_raws) is not tuple or any(type(r) is not saved.SavedRaw for r in saved_raws):
                raise ValueError('exact saved raw declarations required')
            declarations = []
            for raw in saved_raws:
                raw.__post_init__()
                declarations.append([raw.path,raw.sha256,raw.size])
            path = self.timing_root/f'{index:03d}'
            path.mkdir(exist_ok=False)
            intent = self._save(path/'intent.json', dict(schema=SCHEMA,binding_sha256=self.binding_sha256,
                index=index,start_ns=start,previous_terminal_sha256=self._timing_previous,
                expected_head=expected_head,source_identity=expected_source_identity,
                raw_declaration_sha256=io.digest(io.encode(declarations))))
            result = super().step_saved_job(saved_raws,expected_source_identity=expected_source_identity,
                                           expected_head=expected_head)
            if result.completed_hours != index+1: raise ValueError('returned parent hour differs')
            job = self._lease.root/f'job_{index:03d}_non_authoritative'
            job_views = {name:io.read_stable(job/name,saved.CONTENT_CAP) for name in JOB_FILES}
            self._timing_check()
            end = self._now(start)
            terminal = self._save(path/'terminal.json', dict(schema=SCHEMA,intent_sha256=intent,
                end_ns=end,outcome_head=result.head,completed_hours=result.completed_hours,
                status=result.status,job_records={n:io.digest(v[0]) for n,v in job_views.items()},**FLAGS))
            checked = inspect(self.timing_root,index,expected_binding_sha=self.binding_sha256,
                expected_intent_sha=intent,expected_terminal_sha=terminal,
                expected_implementation=self._timing_implementation)
            if checked['outcome_head'] != result.head: raise ValueError('fresh parent reference differs')
            if any(io.read_stable(job/n,saved.CONTENT_CAP) != v for n,v in job_views.items()):
                raise ValueError('Job view changed')
            self._timing_check()
            final = self._now(end)
            self.last_observation = Observation(end-start,final-end,final-start,terminal)
            self._timing_previous = terminal
            self._timing_index += 1
            return result
        except BaseException:
            self._timing_poisoned = True
            self._parent._poisoned = True
            raise
        finally:
            self._timing_guard.release()

    def close(self):
        if self._timing_owner != (os.getpid(),threading.get_ident()):
            raise ValueError('controller close owner differs')
        if not self._timing_guard.acquire(blocking=False): raise ValueError('controller timing active')
        try:
            if self._timing_closed: return
            # Cleanup remains available after poison; never publish successful timing.
            if self._timing_poisoned:
                super().close()
                self._timing_closed = True
                return
            self._timing_check()
            start = self._now(self._last_tick)
            super().close()
            end = self._now(start)
            pin = self._save(self.timing_root/'close.json',dict(schema=SCHEMA,
                binding_sha256=self.binding_sha256,start_ns=start,end_ns=end,
                previous_terminal_sha256=self._timing_previous))
            self._timing_check()
            final = self._now(end)
            self.close_observation = Observation(end-start,final-end,final-start,pin)
            self._timing_closed = True
        except BaseException:
            self._timing_poisoned = True
            super().close()
            raise
        finally:
            self._timing_guard.release()


def additional_content_bound(hours):
    if type(hours) is not int or not 1 <= hours <= 192: raise ValueError('bounded hour count')
    return dict(files=3+2*hours,directories=1+hours,bytes=(3+2*hours)*io.META_CAP)
