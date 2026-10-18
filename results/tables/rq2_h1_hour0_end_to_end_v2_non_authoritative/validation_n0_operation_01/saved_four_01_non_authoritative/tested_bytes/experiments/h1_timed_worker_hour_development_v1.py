"""Owned timed-hour worker envelope; no CLI, Job launch, or native authority.

run() uses the underlying native-capable hour API. A real invocation still needs
separate explicit authorization and Job/resource supervision. Tests replace only
the solver adapter, retaining the actual process and default monotonic clock.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat
import sys
import threading
import time
import types

from experiments import h1_timed_hour_development_v1 as hour
from experiments import h1_saved_job_development_v1 as job

io, timing = hour.io, hour.stage.capture.timing
SCHEMA = 'h1_timed_worker_hour_development_v1'
FLAGS = dict(hour.stage.capture.FLAGS, worker_job_membership_verified=False,
             cross_process_clock_bridge_verified=False)
_CLOCK, _INFO = time.perf_counter_ns, time.get_clock_info
_INIT = timing.Measurement.__init__
_TOKEN = object()


def implementation_identity():
    return io.digest(io.encode([SCHEMA,hour.implementation_identity(),job.implementation_identity(),
                               io.digest(Path(__file__).read_bytes())]))


def clock_profile():
    if (os.name != 'nt' or sys.implementation.name != 'cpython'
            or time.perf_counter_ns is not _CLOCK or time.get_clock_info is not _INFO
            or not isinstance(_CLOCK,types.BuiltinFunctionType)
            or timing.Measurement.__init__ is not _INIT
            or _INIT.__kwdefaults__ != {'clock':_CLOCK}):
        raise ValueError('fixed default worker/native clock required')
    info = _INFO('perf_counter')
    if info.implementation != 'QueryPerformanceCounter()' or not info.monotonic or info.adjustable:
        raise ValueError('fixed monotonic QPC clock required')
    return dict(implementation=info.implementation,monotonic=True,adjustable=False,
                resolution_hex=info.resolution.hex(),python_version=sys.version,units='integer_nanoseconds')


def _integer(x):
    if type(x) is not int or not 0 <= x < 2**63: raise ValueError('bounded exact integer required')
    return x


def _tick(previous=0):
    value = _integer(_CLOCK())
    if value < previous: raise ValueError('worker clock reversal')
    return value


def analyse_intervals(rows, *, count, pid, thread_id, start, end):
    """Arithmetic/owner/containment only; does not authenticate the clock source."""
    if (type(rows) is not list or type(count) is not int or not 1 <= count <= 232
            or len(rows) != count or _integer(pid) == 0 or _integer(thread_id) == 0
            or _integer(end) < _integer(start)):
        raise ValueError('complete bounded interval sequence required')
    previous, total, domains = start, 0, set()
    for index,row in enumerate(rows):
        if type(row) is not dict or set(row) != {'index','pid','thread_id','clock_domain',
                'apply_start_ns','native_start_ns','native_end_ns','apply_end_ns',
                'binding_sha256','terminal_sha256'}:
            raise ValueError('exact interval record required')
        if (type(row['index']) is not int or row['index'] != index
                or _integer(row['pid']) != pid or _integer(row['thread_id']) != thread_id):
            raise ValueError('interval sequence or owner differs')
        domain = row['clock_domain']
        if (type(domain) is not str or len(domain) != 32
                or any(c not in '0123456789abcdef' for c in domain) or domain in domains):
            raise ValueError('distinct stage clock labels required')
        domains.add(domain)
        io.pin(row['binding_sha256']);io.pin(row['terminal_sha256'])
        left,begin,finish,right = (_integer(row[k]) for k in
            ('apply_start_ns','native_start_ns','native_end_ns','apply_end_ns'))
        if not previous <= left <= begin <= finish <= right <= end:
            raise ValueError('disjoint contained stage intervals required')
        total += finish-begin
        previous = right
    return dict(native_total_ns=total,worker_window_ns=end-start,
                worker_window_non_native_ns=end-start-total)


def _read(path, cap=io.META_CAP):
    view = io.read_stable(path,cap)
    doc = json.loads(view[0])
    if io.encode(doc) != view[0]: raise ValueError('canonical worker record required')
    return doc,view


def _intervals(root, count):
    if type(count) is not int or not 1 <= count <= 232: raise ValueError('bounded stage count required')
    rows,views = [],{}
    for index in range(count):
        path = root/'stages'/f'{index:03d}'/'native_timing'
        docs = {}
        for name in ('binding.json','completion.json','terminal.json'):
            doc,view = _read(path/name)
            docs[name] = doc;views[path/name] = view
        binding,complete,terminal = (docs[n] for n in ('binding.json','completion.json','terminal.json'))
        rows.append(dict(index=index,pid=binding['pid'],thread_id=binding['thread_id'],
            clock_domain=binding['clock_domain'],apply_start_ns=terminal['apply_start_ns'],
            native_start_ns=complete['native_start_ns'],native_end_ns=complete['native_end_ns'],
            apply_end_ns=terminal['apply_end_ns'],binding_sha256=io.digest(views[path/'binding.json'][0]),
            terminal_sha256=io.digest(views[path/'terminal.json'][0])))
    return rows,views


def _unchanged(views):
    if any(io.read_stable(path,io.META_CAP) != view for path,view in views.items()):
        raise ValueError('worker interval evidence changed')


def _root(root):
    if root.absolute() != root.resolve(): raise ValueError('canonical worker root required')
    info = root.stat(follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode) or getattr(info,'st_file_attributes',0) & 0x400:
        raise ValueError('plain worker directory required')
    names = set()
    with os.scandir(root) as entries:
        for entry in entries:
            names.add(entry.name)
            if len(names) > 4: raise ValueError('worker entry cap')
    if names != {'execution.lock','binding.json','terminal.json','hour_non_authoritative'}:
        raise ValueError('worker topology differs')
    return info.st_dev,info.st_ino


def inspect(root, packet, specification, limits, *, expected_binding_sha,
            expected_terminal_sha, expected_implementation):
    """Conditional complete-hour replay, not proof of live clock/Job membership."""
    for pin in (expected_binding_sha,expected_terminal_sha,expected_implementation): io.pin(pin)
    if implementation_identity() != expected_implementation: raise ValueError('worker implementation differs')
    root = Path(root).absolute()
    identity = _root(root)
    binding,bv = _read(root/'binding.json')
    terminal,tv = _read(root/'terminal.json')
    if io.digest(bv[0]) != expected_binding_sha or io.digest(tv[0]) != expected_terminal_sha:
        raise ValueError('external worker pin differs')
    if (set(binding) != {'schema','implementation','hour_request_sha256','controller_request_sha256',
            'pid','creation_filetime','thread_id','clock','start_ns',*FLAGS}
            or binding['schema'] != SCHEMA or binding['implementation'] != expected_implementation
            or binding['hour_request_sha256'] != hour.request_key(packet,specification,limits)
            or binding['clock'] != clock_profile() or any(binding[k] is not False for k in FLAGS)):
        raise ValueError('worker binding differs')
    io.pin(binding['controller_request_sha256'])
    if _integer(binding['creation_filetime']) == 0: raise ValueError('process creation identity required')
    if (set(terminal) != {'schema','binding_sha256','end_ns','hour_terminal_sha256',
                         'interval_vector_sha256','native_total_ns','worker_window_non_native_ns',*FLAGS}
            or terminal['schema'] != SCHEMA or terminal['binding_sha256'] != expected_binding_sha
            or any(terminal[k] is not False for k in FLAGS)):
        raise ValueError('worker terminal differs')
    count = len(hour.prior.native.model_api.stage_order(packet.inputs))
    rows,views = _intervals(root/'hour_non_authoritative',count)
    full_view = hour._snapshot(root/'hour_non_authoritative',count,True)
    result = hour.inspect(root/'hour_non_authoritative',packet,specification,limits,
        expected_terminal_sha=terminal['hour_terminal_sha256'],expected_implementation=hour.implementation_identity())
    values = analyse_intervals(rows,count=count,pid=binding['pid'],thread_id=binding['thread_id'],
                               start=binding['start_ns'],end=terminal['end_ns'])
    if (io.digest(io.encode(rows)) != terminal['interval_vector_sha256']
            or _integer(terminal['native_total_ns']) != values['native_total_ns']
            or result['native_total_ns'] != values['native_total_ns']
            or _integer(terminal['worker_window_non_native_ns']) != values['worker_window_non_native_ns']):
        raise ValueError('worker native total/vector differs')
    views.update({root/'binding.json':bv,root/'terminal.json':tv})
    _unchanged(views)
    if (hour._snapshot(root/'hour_non_authoritative',count,True) != full_view
            or _root(root) != identity
            or implementation_identity() != expected_implementation):
        raise ValueError('worker root/implementation changed')
    return dict(values,projection_payload=result['projection_payload'],
        interval_vector_sha256=terminal['interval_vector_sha256'],clock_source_authenticated=False,
        owned_run_return_observed=False,confirmation_tail_ns=None,**FLAGS)


@dataclass(frozen=True,init=False)
class Completion:
    root: str
    terminal_sha256: str
    hour_terminal_sha256: str
    projection_payload: bytes
    native_total_ns: int
    worker_window_non_native_ns: int
    confirmation_tail_ns: int
    local_clock_binding_checked: bool
    authority_flags: tuple

    def __init__(self, values, *, _token=None):
        if _token is not _TOKEN: raise TypeError('owned worker hour required')
        for name,value in zip(self.__annotations__,values,strict=True):object.__setattr__(self,name,value)


class OwnedWorkerHour:
    def __init__(self,root,packet,specification,limits,*,controller_request_sha256,
                 expected_pid,expected_creation_filetime):
        self.start = _tick()
        self.clock = clock_profile()
        actual = job._current_process()
        if (type(expected_pid) is not int or type(expected_creation_filetime) is not int
                or actual != (expected_pid,expected_creation_filetime)):
            raise ValueError('actual worker process identity differs')
        io.pin(controller_request_sha256)
        self.owner = actual+(threading.get_ident(),)
        self.context = packet,specification,limits
        self.key = hour.request_key(*self.context)
        self.implementation = implementation_identity()
        self.guard = threading.Lock()
        self.started = self.poisoned = self.complete = False
        self._lease = job.bounded.chunks.base.local._Lease(Path(root),True)
        self.root = self._lease.root
        try:
            self.binding = dict(schema=SCHEMA,implementation=self.implementation,hour_request_sha256=self.key,
                controller_request_sha256=controller_request_sha256,pid=actual[0],creation_filetime=actual[1],
                thread_id=self.owner[2],clock=self.clock,start_ns=self.start,**FLAGS)
            self.binding_pin = io.write_metadata(self.root/'binding.json',self.binding)
            self.binding_view = io.read_stable(self.root/'binding.json',io.META_CAP)
            if self.binding_view[0] != io.encode(self.binding) or io.digest(self.binding_view[0]) != self.binding_pin:
                raise ValueError('worker binding confirmation differs')
        except BaseException:
            self._release()
            raise

    def _release(self):
        lease,self._lease = self._lease,None
        if lease is not None: lease.close()

    def _check(self):
        if (self._lease is None or self.poisoned or self.complete
                or job._current_process()+(threading.get_ident(),) != self.owner
                or clock_profile() != self.clock or implementation_identity() != self.implementation
                or hour.request_key(*self.context) != self.key
                or io.read_stable(self.root/'binding.json',io.META_CAP) != self.binding_view):
            raise ValueError('worker state/owner/clock/context differs')
        self._lease.check()

    def run(self):
        if not self.guard.acquire(blocking=False): raise ValueError('worker hour active')
        try:
            self._check()
            if self.started: raise ValueError('worker hour consumed')
            self.started = True
            producer = hour.OwnedHour(self.root/'hour_non_authoritative',*self.context)
            receipt = producer.run()
            if (type(receipt) is not hour.HourCompletion or not producer.complete or producer.poisoned
                    or receipt.root != str(producer.root) or receipt.request_sha256 != self.key
                    or receipt.implementation != hour.implementation_identity()
                    or receipt.authority_flags != tuple(hour.stage.capture.FLAGS.items())):
                raise ValueError('owned hour receipt differs')
            full_view = hour._snapshot(producer.root,producer.count,True)
            fresh = hour.inspect(producer.root,*self.context,expected_terminal_sha=receipt.terminal_sha256,
                                 expected_implementation=receipt.implementation)
            rows,views = _intervals(producer.root,producer.count)
            _unchanged(views)
            self._check()
            end = _tick(self.start)
            values = analyse_intervals(rows,count=producer.count,pid=self.owner[0],thread_id=self.owner[2],
                                       start=self.start,end=end)
            if (values['native_total_ns'] != receipt.native_total_ns
                    or fresh['native_total_ns'] != receipt.native_total_ns
                    or fresh['projection_payload'] != receipt.projection_payload):
                raise ValueError('owned/fresh hour differs')
            pin = io.write_metadata(self.root/'terminal.json',dict(schema=SCHEMA,binding_sha256=self.binding_pin,
                end_ns=end,hour_terminal_sha256=receipt.terminal_sha256,
                interval_vector_sha256=io.digest(io.encode(rows)),native_total_ns=values['native_total_ns'],
                worker_window_non_native_ns=values['worker_window_non_native_ns'],**FLAGS))
            checked = inspect(self.root,*self.context,expected_binding_sha=self.binding_pin,
                expected_terminal_sha=pin,expected_implementation=self.implementation)
            if checked['projection_payload'] != receipt.projection_payload: raise ValueError('worker projection differs')
            _unchanged(views)
            self._check()
            if hour._snapshot(producer.root,producer.count,True) != full_view:
                raise ValueError('full hour view changed before worker completion')
            self._release()
            final = _tick(end)
            result = Completion((str(self.root),pin,receipt.terminal_sha256,receipt.projection_payload,
                values['native_total_ns'],values['worker_window_non_native_ns'],final-end,True,tuple(FLAGS.items())),_token=_TOKEN)
            self.complete = True
            return result
        except BaseException:
            self.poisoned = True
            raise
        finally:
            try: self._release()
            finally: self.guard.release()

    def close(self):
        if job._current_process()+(threading.get_ident(),) != self.owner: raise ValueError('worker close owner differs')
        if not self.guard.acquire(blocking=False): raise ValueError('worker hour active')
        try:
            if not self.complete: self.poisoned = True
            self._release()
        finally: self.guard.release()
