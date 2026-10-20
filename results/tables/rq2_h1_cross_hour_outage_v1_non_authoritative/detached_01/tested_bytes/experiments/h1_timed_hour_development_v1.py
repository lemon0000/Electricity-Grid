"""Sequential owned native-stage hour, development only.

run() can execute native code and needs separately authorized Job supervision.
No CLI, resume, partial projection, native authentication or formal authority.
"""
from dataclasses import asdict, dataclass
import os
from pathlib import Path
import stat
import threading

from experiments import h1_timed_stage_development_v1 as stage

science, io = stage.science, stage.io
prior = science.prior
SCHEMA = 'h1_timed_hour_development_v1'
PROJECTION_CAP = 256 * 1024
_TOKEN = object()


def implementation_identity():
    return io.digest(io.encode(dict(schema=SCHEMA, stage=stage.implementation_identity(),
        own=io.digest(Path(__file__).read_bytes()))))


def request_key(packet, specification, limits):
    return io.digest(io.encode(dict(schema=SCHEMA, scientific_request=prior.request_key(packet, specification, limits),
        packet_audit_identity=packet.audit_identity, implementation=implementation_identity())))


def _binding(key, count, packet, specification, limits):
    return dict(schema=SCHEMA, request_sha256=key, stages=count,
        input_identity=packet.input_identity, packet_audit_identity=packet.audit_identity,
        relative_hour=packet.relative_hour, specification_sha256=io.digest(io.encode(asdict(specification))),
        limits_sha256=io.digest(io.encode(asdict(limits))),
        stage_order_sha256=io.digest(io.encode(prior.native.model_api.stage_order(packet.inputs))),
        implementation=implementation_identity(), stage_implementation=stage.implementation_identity(), **stage.capture.FLAGS)


def _commit(key, previous, index, locks, complete_pin, science_pin, result, context):
    return dict(schema=SCHEMA, request_sha256=key, previous_sha256=previous, stage=index,
        prefix_sha256=io.digest(io.encode([x.hex() for x in locks])),
        stage_request_sha256=science.request_key(*context, index, locks), child=f'stages/{index:03d}',
        stage_implementation=stage.implementation_identity(),
        producer_complete_sha256=complete_pin, science_terminal_sha256=science_pin,
        stage_identity=result['stage_identity'], lock_hex=result['lock'].hex(),
        native_sha256=result['native_sha256'], numerical_sha256=io.digest(io.encode(result['numerical'])),
        timing_binding_sha256=result['timing']['binding_sha256'],
        timing_terminal_sha256=result['timing']['terminal_sha256'],
        native_interval_ns=result['timing']['native_interval_ns'],
        **stage.capture.FLAGS)


def _projection(packet, key, locks, assignment, vector_pin, timing_vector_pin, native_total):
    # Reuse the approved boundary transition, without constructing an old-v3
    # replay object or claiming that capsule bytes are old native reports.
    transition = prior.current.source.replay_feasible_boundary(packet, assignment,
        expected_input_identity=packet.input_identity)
    after = transition.candidate_boundary
    return io.encode(dict(schema=SCHEMA, request_sha256=key, before_identity=transition.before_identity,
        stage_vector_sha256=vector_pin, implementation=implementation_identity(),
        timing_vector_sha256=timing_vector_pin, native_total_ns=native_total, native_intervals_complete=True,
        value=dict(network_identity=after.network_identity, completed_hours=after.completed_hours,
            units=[[uid, on, float(power).hex(), age] for uid, on, power, age in after.units],
            canonical_locks=[x.hex() for x in locks],
            generation_projection_rule=prior.generation_projection.rule.implementation_identity()),
        **stage.capture.FLAGS))


def _terminal(key, binding_pin, head, payload, count, vector_pin, timing_vector_pin, native_total):
    return dict(schema=SCHEMA, request_sha256=key, binding_sha256=binding_pin,
        last_commit_sha256=head, projection_sha256=io.digest(payload), stages=count,
        stage_vector_sha256=vector_pin,
        timing_vector_sha256=timing_vector_pin, native_total_ns=native_total, native_intervals_complete=True,
        projection_identity=io.digest(io.encode([SCHEMA+'_projection', io.digest(payload)])),
        **stage.capture.FLAGS)


def _directory(path, expected):
    info = path.stat(follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('plain hour directory required')
    # Stop after one excess entry rather than allocate an unbounded listing.
    names = set()
    with os.scandir(path) as entries:
        for item in entries:
            names.add(item.name)
            if len(names) > len(expected): raise ValueError('hour directory entry cap')
    if names != expected: raise ValueError('hour topology differs')
    return info.st_dev, info.st_ino


def _snapshot(root, count, terminal):
    dirs = {'.': _directory(root, {'binding.json', 'stages', 'commits'} |
                           ({'projection.bin', 'terminal.json'} if terminal else set())),
        'stages': _directory(root/'stages', {f'{i:03d}' for i in range(count)}),
        'commits': _directory(root/'commits', {f'{i:03d}.json' for i in range(count)})}
    caps = {'binding.json': io.META_CAP}
    if terminal: caps.update({'projection.bin': PROJECTION_CAP, 'terminal.json': io.META_CAP})
    for i in range(count):
        prefix = f'stages/{i:03d}'
        dirs.update({prefix+'/'+n: v for n, v in stage._layout(root/prefix).items()})
        caps.update({prefix+'/'+n: cap for n, cap in stage._FILES.items()})
        caps[f'commits/{i:03d}.json'] = io.META_CAP
    files = {}
    for name, cap in caps.items():
        raw, stamp = io.read_stable(root/name, cap)
        files[name] = (io.digest(raw), stamp, cap)
    return dirs, files


def _replay(root, packet, specification, limits, *, terminal):
    key = request_key(packet, specification, limits)
    count = len(prior.native.model_api.stage_order(packet.inputs))
    if not 1 <= count <= 232: raise ValueError('hour stage envelope')
    implementation = implementation_identity()
    view = _snapshot(root, count, terminal)
    binding_raw = io.read_stable(root/'binding.json', io.META_CAP)[0]
    if binding_raw != io.encode(_binding(key, count, packet, specification, limits)): raise ValueError('hour binding differs')
    binding_pin = head = io.digest(binding_raw)
    locks, assignment = (), None
    vector = []
    timing_vector = []
    for index in range(count):
        path = root/'commits'/f'{index:03d}.json'
        raw = io.read_stable(path, io.META_CAP)[0]
        doc = prior.old._decode(raw, io.META_CAP)
        result = stage.inspect(root/'stages'/f'{index:03d}', packet, specification, limits, index, locks,
            expected_producer_complete_sha=doc['producer_complete_sha256'],
            expected_science_terminal_sha=doc['science_terminal_sha256'],
            expected_implementation=stage.implementation_identity())['result']
        if raw != io.encode(_commit(key, head, index, locks, doc['producer_complete_sha256'],
                                    doc['science_terminal_sha256'], result, (packet, specification, limits))):
            raise ValueError('hour commit/lock chain differs')
        head = io.digest(raw)
        vector.append([doc['producer_complete_sha256'], doc['science_terminal_sha256'], head])
        if result['timing']['interval_complete'] is not True: raise ValueError('native interval incomplete')
        timing_vector.append([index, science.request_key(packet, specification, limits, index, locks),
            result['timing']['clock_domain'], result['timing']['binding_sha256'],
            result['timing']['terminal_sha256'], result['timing']['native_interval_ns']])
        locks = (*locks, result['lock'])
        assignment = result['assignment']
    if not locks: raise ValueError('empty hour sequence')
    vector_pin = io.digest(io.encode(vector))
    timing_vector_pin = io.digest(io.encode(timing_vector))
    native_total = sum(row[-1] for row in timing_vector)
    payload = _projection(packet, key, locks, assignment, vector_pin, timing_vector_pin, native_total)
    if len(payload) > PROJECTION_CAP: raise ValueError('hour projection exceeds cap')
    if terminal:
        if io.read_stable(root/'projection.bin', PROJECTION_CAP)[0] != payload:
            raise ValueError('hour projection differs')
        if io.read_stable(root/'terminal.json', io.META_CAP)[0] != io.encode(_terminal(key, binding_pin, head, payload, count, vector_pin,
                timing_vector_pin, native_total)):
            raise ValueError('hour terminal differs')
    if (_snapshot(root, count, terminal) != view or request_key(packet, specification, limits) != key
            or implementation_identity() != implementation):
        raise ValueError('hour view/context changed during replay')
    return dict(key=key, binding_pin=binding_pin, head=head, payload=payload, locks=locks, vector_pin=vector_pin,
                timing_vector_pin=timing_vector_pin, native_total=native_total)


def inspect(root, packet, specification, limits, *, expected_terminal_sha, expected_implementation):
    """Full-hour zero-solver replay; never reconstructs an owned completion."""
    with prior.guard.solver_calls_forbidden():
        io.pin(expected_terminal_sha); io.pin(expected_implementation)
        root = Path(root).absolute()
        if root.resolve() != root: raise ValueError('canonical hour root required')
        if implementation_identity() != expected_implementation: raise ValueError('hour implementation differs')
        terminal = io.read_stable(root/'terminal.json', io.META_CAP)
        if io.digest(terminal[0]) != expected_terminal_sha: raise ValueError('external hour pin differs')
        result = _replay(root, packet, specification, limits, terminal=True)
        if (io.read_stable(root/'terminal.json', io.META_CAP) != terminal or
                implementation_identity() != expected_implementation):
            raise ValueError('hour terminal/implementation changed')
        return dict(projection_payload=result['payload'], canonical_locks=result['locks'],
            native_total_ns=result['native_total'], timing_vector_sha256=result['timing_vector_pin'],
            native_intervals_complete=True,
            full_hour_chain_recomputed=True, owned_run_return_observed=False,
            whole_job_quiescence_checked=False, **stage.capture.FLAGS)


@dataclass(frozen=True, init=False)
class HourCompletion:
    root: str
    terminal_sha256: str
    implementation: str
    request_sha256: str
    projection_payload: bytes
    native_total_ns: int
    timing_vector_sha256: str
    authority_flags: tuple

    def __init__(self, root, pin, implementation, key, payload, native_total, timing_vector_pin, *, _token=None):
        if _token is not _TOKEN: raise TypeError('owned full hour required')
        for name, item in zip(self.__annotations__, (str(root), pin, implementation, key, payload, native_total, timing_vector_pin,
                                                    tuple(stage.capture.FLAGS.items()))):
            object.__setattr__(self, name, item)


class OwnedHour:
    def __init__(self, root, packet, specification, limits):
        self.root = Path(root).absolute()
        if self.root.resolve() != self.root: raise ValueError('canonical hour root required')
        self.context = (packet, specification, limits)
        self.key = request_key(*self.context)
        self.implementation = implementation_identity()
        self.count = len(prior.native.model_api.stage_order(packet.inputs))
        if not 1 <= self.count <= 232: raise ValueError('hour stage envelope')
        self.owner = (os.getpid(), threading.get_ident())
        self.guard = threading.Lock()
        self.started = self.poisoned = self.complete = False
        self.root.mkdir(exist_ok=False)
        (self.root/'stages').mkdir(); (self.root/'commits').mkdir()
        self.binding_pin = io.write_metadata(self.root/'binding.json', _binding(self.key, self.count, *self.context))

    def _check(self):
        if (self.owner != (os.getpid(), threading.get_ident()) or
                implementation_identity() != self.implementation or request_key(*self.context) != self.key or
                io.digest(io.read_stable(self.root/'binding.json', io.META_CAP)[0]) != self.binding_pin):
            raise ValueError('hour owner/context differs')

    def run(self):
        if not self.guard.acquire(blocking=False): raise ValueError('hour active')
        try:
            self._check()
            if self.started or self.poisoned or self.complete: raise ValueError('hour already consumed')
            self.started = True
            locks, head = (), self.binding_pin
            for index in range(self.count):
                self._check()
                path = self.root/'stages'/f'{index:03d}'
                producer = stage.OwnedStage(path, *self.context, index, locks)
                receipt = producer.run()
                if (type(receipt) is not stage.Completion or not producer.complete or producer.poisoned or
                        receipt.root != str(path) or receipt.request_sha256 != science.request_key(*self.context, index, locks) or
                        receipt.implementation != stage.implementation_identity() or
                        receipt.authority_flags != tuple(stage.capture.FLAGS.items())):
                    raise ValueError('owned stage completion differs')
                with prior.guard.solver_calls_forbidden():
                    result = stage.inspect(path, *self.context, index, locks,
                        expected_producer_complete_sha=receipt.producer_complete_sha256,
                        expected_science_terminal_sha=receipt.science_terminal_sha256,
                        expected_implementation=receipt.implementation)['result']
                    self._check()
                    head = io.write_metadata(self.root/'commits'/f'{index:03d}.json',
                        _commit(self.key, head, index, locks, receipt.producer_complete_sha256,
                                receipt.science_terminal_sha256, result, self.context))
                    self._check()
                    locks = (*locks, result['lock'])
            with prior.guard.solver_calls_forbidden():
                fresh = _replay(self.root, *self.context, terminal=False)
                if fresh['locks'] != locks or fresh['head'] != head: raise ValueError('fresh hour differs')
                io.write_new(self.root/'projection.bin', fresh['payload'])
                pin = io.write_metadata(self.root/'terminal.json', _terminal(self.key, self.binding_pin,
                    head, fresh['payload'], self.count, fresh['vector_pin'], fresh['timing_vector_pin'], fresh['native_total']))
                checked = inspect(self.root, *self.context, expected_terminal_sha=pin,
                                  expected_implementation=self.implementation)
                self._check()
                receipt = HourCompletion(self.root, pin, self.implementation, self.key,
                    checked['projection_payload'], checked['native_total_ns'], checked['timing_vector_sha256'], _token=_TOKEN)
            self.complete = True
            return receipt
        except BaseException:
            self.poisoned = True
            raise
        finally:
            self.guard.release()
