"""Owned stage completion handshake; development only.

run() can execute native code. A future caller needs separate explicit authority
and Job/resource supervision. Tests use synthetic adapters. No CLI or resume.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import stat
import threading

from experiments import h1_timed_native_science_development_v1 as science

io = science.io
capture = science.capture
SCHEMA = 'h1_timed_stage_development_v1'
_TOKEN = object()
_FILES = {
    'capture/binding.json': io.META_CAP, 'capture/specification.json': io.META_CAP,
    'capture/export.json': io.META_CAP, 'capture/complete.json': io.META_CAP,
    'capture/native_raw/binding.json': io.META_CAP,
    'capture/native_raw/terminal.json': io.META_CAP,
    'capture/native_raw/000/intent.json': io.META_CAP,
    'capture/native_raw/000/raw.bin': io.RAW_CAP,
    'capture/native_raw/000/raw_receipt.json': io.META_CAP,
    'capture/native_raw/000/outcome.json': io.META_CAP,
    **{'capture/science/'+n: cap for n, cap in (
        ('intent.json', io.META_CAP), ('postsolve_receipt.json', io.META_CAP),
        ('terminal.json', io.META_CAP), ('postsolve.bin', science.POST_CAP),
        ('numerical.bin', io.RAW_CAP), ('mapping.bin', science.POST_CAP),
        ('result.bin', science.POST_CAP))},
}
_FILES = {n.removeprefix('capture/'): cap for n, cap in _FILES.items()}
_FILES.update({'native_timing/'+name: io.META_CAP for name in
               ('binding.json', 'intent.json', 'completion.json', 'terminal.json')})


def implementation_identity():
    return io.digest(io.encode(dict(schema=SCHEMA, science=science.implementation_identity(),
        own=io.digest(Path(__file__).read_bytes()))))


def _layout(root):
    names = set(_FILES)
    directories = {''}
    for name in names:
        directories.update(p.as_posix() for p in Path(name).parents if p.as_posix() != '.')
    stamps = {}
    for name in sorted(directories):
        path = root/name
        info = path.stat(follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('plain directory required')
        expected = {n[len(name)+1:] if name else n for n in names | directories
                    if n != name and str(Path(n).parent).replace('\\', '/') == (name or '.')}
        if {p.name for p in path.iterdir()} != expected:
            raise ValueError('completion topology differs')
        stamps[name] = (info.st_dev, info.st_ino)
    return stamps


def _views(root):
    layout = _layout(root)
    return layout, {name: io.read_stable(root/name, cap) for name, cap in _FILES.items()}


def _unchanged(root, layout, views):
    if _layout(root) != layout:
        raise ValueError('completion directories changed')
    for name, (raw, stamp) in views.items():
        if io.read_stable(root/name, len(raw)) != (raw, stamp):
            raise ValueError('completion view changed')


def _records(root, packet, specification, limits, index, locks, *, complete_pin, science_pin):
    for pin in (complete_pin, science_pin): io.pin(pin)
    key = science.request_key(packet, specification, limits, index, locks)
    implementation = implementation_identity()
    layout, views = _views(root)
    raw = {n: view[0] for n, view in views.items()}
    if (io.digest(raw['complete.json']) != complete_pin or
            io.digest(raw['science/terminal.json']) != science_pin):
        raise ValueError('external completion pins differ')
    expected = dict(schema=capture.SCHEMA,
        binding_sha256=io.digest(raw['binding.json']),
        raw_sha256=io.digest(raw['native_raw/000/raw.bin']),
        timing_binding_sha256=io.digest(raw['native_timing/binding.json']),
        timing_terminal_sha256=io.digest(raw['native_timing/terminal.json']),
        raw_terminal_sha256=io.digest(raw['native_raw/terminal.json']),
        callback_sequence_complete=True, **capture.FLAGS)
    if raw['complete.json'] != io.encode(expected):
        raise ValueError('producer completion record differs')
    ingress = io.inspect(root/'native_raw', expected_request=key,
        expected_binding_sha256=io.digest(raw['native_raw/binding.json']))
    if not ingress['callback_sequence_complete'] or ingress['errors']:
        raise ValueError('producer ingress incomplete')
    intent = science.prior.old._decode(raw['science/intent.json'], io.META_CAP)
    if (intent['timing_binding_sha256'] != expected['timing_binding_sha256'] or
            intent['timing_terminal_sha256'] != expected['timing_terminal_sha256']):
        raise ValueError('capture/science timing pins differ')
    if intent['native_path'] != str((root/'native_raw/000/raw.bin').resolve()):
        raise ValueError('science references foreign producer')
    result = science.inspect(root/'science', packet, specification, limits, index, locks,
                             expected_terminal_sha=science_pin)
    timing = capture.timing.inspect(root/'native_timing',
        expected_binding_sha=expected['timing_binding_sha256'],
        expected_terminal_sha=expected['timing_terminal_sha256'],
        expected_implementation=capture.timing.implementation_identity())
    timing_binding = science.prior.old._decode(raw['native_timing/binding.json'], io.META_CAP)
    if timing_binding['stage'] != index or timing_binding['request_sha256'] != key:
        raise ValueError('timing context differs')
    result = dict(result, timing=dict(timing, binding_sha256=expected['timing_binding_sha256'],
        terminal_sha256=expected['timing_terminal_sha256'], clock_domain=timing_binding['clock_domain']))
    _unchanged(root, layout, views)
    if (science.request_key(packet, specification, limits, index, locks) != key or
            implementation_identity() != implementation):
        raise ValueError('completion inputs changed')
    return result


def inspect(root, packet, specification, limits, index, locks, *,
            expected_producer_complete_sha, expected_science_terminal_sha, expected_implementation):
    """Read-only conditional evidence. Never mints an in-memory run receipt."""
    with science.prior.guard.solver_calls_forbidden():
        io.pin(expected_implementation)
        if implementation_identity() != expected_implementation:
            raise ValueError('completion reader implementation differs')
        root = Path(root).absolute()
        if root.resolve() != root: raise ValueError('canonical completion root required')
        result = _records(root, packet, specification, limits, index, locks,
            complete_pin=expected_producer_complete_sha, science_pin=expected_science_terminal_sha)
        if implementation_identity() != expected_implementation:
            raise ValueError('completion reader implementation changed')
        return dict(result=result, producer_completion_record_checked=True,
            producer_run_return_observed=False, whole_job_quiescence_checked=False, **capture.FLAGS)


@dataclass(frozen=True, init=False)
class Completion:
    root: str
    request_sha256: str
    implementation: str
    producer_complete_sha256: str
    science_terminal_sha256: str
    authority_flags: tuple

    def __init__(self, root, request_sha, implementation, complete_sha, science_sha, *, _token=None):
        if _token is not _TOKEN: raise TypeError('owned successful run required')
        for name, item in zip(self.__annotations__, (str(root), request_sha, implementation, complete_sha,
                                                    science_sha, tuple(capture.FLAGS.items()))):
            object.__setattr__(self, name, item)


class OwnedStage:
    """One owner, one run; publication errors poison and never return Completion."""
    def __init__(self, root, packet, specification, limits, index, locks):
        self.root = Path(root).absolute()
        if self.root.resolve() != self.root: raise ValueError('canonical completion root required')
        if self.root.exists(): raise FileExistsError(self.root)
        self.context = (packet, specification, limits, index, tuple(locks))
        self.key = science.request_key(*self.context)
        self.implementation = implementation_identity()
        self.owner = (os.getpid(), threading.get_ident())
        self.guard = threading.Lock()
        self.started = self.poisoned = self.complete = False

    def _check(self):
        if self.owner != (os.getpid(), threading.get_ident()): raise ValueError('stage owner differs')
        if implementation_identity() != self.implementation or science.request_key(*self.context) != self.key:
            raise ValueError('owned stage context changed')

    def run(self):
        if not self.guard.acquire(blocking=False): raise ValueError('stage active')
        try:
            self._check()
            if self.started or self.poisoned or self.complete: raise ValueError('stage already consumed')
            self.started = True
            packet, specification, limits, index, locks = self.context
            request = science.prior.native.model_api.H1StageRequest(packet.inputs, locks)
            model = science.prior.native.model_api.build_h1_stage_model(request,
                expected_identity=science.prior.native.model_api.h1_stage_identity(request))
            producer = capture.StageCapture(self.root, request_sha256=self.key,
                expected_structure=capture.old.audit._structure(model),
                expected_implementation=capture.implementation_identity(), stage_index=index)
            callback_answer = None
            def callback(raw, results, actual_model):
                nonlocal callback_answer
                if callback_answer is not None: raise ValueError('second science callback')
                callback_answer = science.consume(producer.root/'science', producer.raw.root/'000/raw.bin',
                    results, actual_model, *self.context, expected_native_sha=io.digest(raw),
                    expected_binding=producer.binding_sha, expected_export=producer.records['export.json'],
                    expected_timing_binding=producer.timing_receipt['binding_sha256'],
                    expected_timing_terminal=producer.timing_receipt['terminal_sha256'])
                return callback_answer
            answer = producer.run(lambda: model, specification, callback)
            if (producer.started is not True or producer.complete is not True or producer.poisoned is not False or
                    producer.owner != self.owner or producer.guard.locked() or answer is not callback_answer or
                    producer.raw.closed is not True or producer.raw.poisoned is not False or producer.raw.next_stage != 1):
                raise ValueError('owned producer did not complete')
            self._check()
            complete_pin = io.digest(io.read_stable(producer.root/'complete.json', io.META_CAP)[0])
            science_pin = answer['terminal_sha256']
            with science.prior.guard.solver_calls_forbidden():
                inspect(self.root, *self.context, expected_producer_complete_sha=complete_pin,
                        expected_science_terminal_sha=science_pin, expected_implementation=self.implementation)
            self._check()
            receipt = Completion(self.root, self.key, self.implementation, complete_pin, science_pin, _token=_TOKEN)
            self.complete = True
            return receipt
        except BaseException:
            self.poisoned = True
            raise
        finally:
            self.guard.release()
