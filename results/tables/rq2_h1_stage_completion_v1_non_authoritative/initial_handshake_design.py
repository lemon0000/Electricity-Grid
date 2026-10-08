"""Owned stage completion handshake; development only.

run() can execute native code. A future caller needs separate explicit authority
and Job/resource supervision. Tests use synthetic adapters. No CLI or resume.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import stat
import threading

from experiments import h1_native_raw_science_development_v1 as science

io = science.io
capture = science.capture
SCHEMA = 'h1_stage_completion_development_v1'
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
    'intent.json': io.META_CAP,
}


def implementation_identity():
    return io.digest(io.encode(dict(schema=SCHEMA, science=science.implementation_identity(),
        own=io.digest(Path(__file__).read_bytes()))))


def _layout(root, *, handshake):
    names = set(_FILES) | ({'handshake.json'} if handshake else set())
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


def _views(root, *, handshake):
    layout = _layout(root, handshake=handshake)
    caps = dict(_FILES)
    if handshake: caps['handshake.json'] = io.META_CAP
    return layout, {name: io.read_stable(root/name, cap) for name, cap in caps.items()}


def _unchanged(root, layout, views, *, handshake):
    if _layout(root, handshake=handshake) != layout:
        raise ValueError('completion directories changed')
    for name, (raw, stamp) in views.items():
        if io.read_stable(root/name, len(raw)) != (raw, stamp):
            raise ValueError('completion view changed')


def _intent(key):
    return dict(schema=SCHEMA, request_sha256=key, implementation=implementation_identity(), **capture.FLAGS)


def _records(root, packet, specification, limits, index, locks, *, complete_pin, science_pin, handshake):
    for pin in (complete_pin, science_pin): io.pin(pin)
    key = science.request_key(packet, specification, limits, index, locks)
    layout, views = _views(root, handshake=handshake)
    raw = {n: view[0] for n, view in views.items()}
    if raw['intent.json'] != io.encode(_intent(key)):
        raise ValueError('completion context differs')
    if (io.digest(raw['capture/complete.json']) != complete_pin or
            io.digest(raw['capture/science/terminal.json']) != science_pin):
        raise ValueError('external completion pins differ')
    expected = dict(schema=capture.SCHEMA,
        binding_sha256=io.digest(raw['capture/binding.json']),
        raw_sha256=io.digest(raw['capture/native_raw/000/raw.bin']),
        raw_terminal_sha256=io.digest(raw['capture/native_raw/terminal.json']),
        callback_sequence_complete=True, **capture.FLAGS)
    if raw['capture/complete.json'] != io.encode(expected):
        raise ValueError('producer completion record differs')
    ingress = io.inspect(root/'capture/native_raw', expected_request=key,
        expected_binding_sha256=io.digest(raw['capture/native_raw/binding.json']))
    if not ingress['callback_sequence_complete'] or ingress['errors']:
        raise ValueError('producer ingress incomplete')
    intent = science.prior.old._decode(raw['capture/science/intent.json'], io.META_CAP)
    if intent['native_path'] != str((root/'capture/native_raw/000/raw.bin').resolve()):
        raise ValueError('science references foreign producer')
    result = science.inspect(root/'capture/science', packet, specification, limits, index, locks,
                             expected_terminal_sha=science_pin)
    _unchanged(root, layout, views, handshake=handshake)
    if science.request_key(packet, specification, limits, index, locks) != key:
        raise ValueError('completion inputs changed')
    pins = {n: io.digest(data) for n, (data, _) in views.items() if n != 'handshake.json'}
    return result, io.digest(io.encode(pins)), layout, views


def _handshake(key, complete_pin, science_pin, view_pin):
    return dict(schema=SCHEMA, request_sha256=key, implementation=implementation_identity(),
        producer_complete_sha256=complete_pin, science_terminal_sha256=science_pin,
        full_view_sha256=view_pin, producer_completion_record_checked=True,
        **capture.FLAGS)


def inspect(root, packet, specification, limits, index, locks, *, expected_handshake_sha):
    """Read-only conditional evidence. Never mints an in-memory run receipt."""
    with science.prior.guard.solver_calls_forbidden():
        io.pin(expected_handshake_sha)
        root = Path(root).absolute()
        raw, stamp = io.read_stable(root/'handshake.json', io.META_CAP)
        if io.digest(raw) != expected_handshake_sha:
            raise ValueError('external handshake pin differs')
        doc = science.prior.old._decode(raw, io.META_CAP)
        result, view_pin, layout, views = _records(root, packet, specification, limits, index, locks,
            complete_pin=doc['producer_complete_sha256'], science_pin=doc['science_terminal_sha256'], handshake=True)
        key = science.request_key(packet, specification, limits, index, locks)
        if raw != io.encode(_handshake(key, doc['producer_complete_sha256'], doc['science_terminal_sha256'], view_pin)):
            raise ValueError('handshake differs')
        if views['handshake.json'] != (raw, stamp): raise ValueError('handshake changed')
        _unchanged(root, layout, views, handshake=True)
        return dict(result=result, producer_completion_record_checked=True,
            producer_run_return_observed=False, whole_job_quiescence_checked=False, **capture.FLAGS)


@dataclass(frozen=True, init=False)
class Completion:
    root: str
    handshake_sha256: str
    producer_complete_sha256: str
    science_terminal_sha256: str

    def __init__(self, root, handshake_sha, complete_sha, science_sha, *, _token=None):
        if _token is not _TOKEN: raise TypeError('owned successful run required')
        for name, item in zip(self.__annotations__, (str(root), handshake_sha, complete_sha, science_sha)):
            object.__setattr__(self, name, item)


class OwnedStage:
    """One owner, one run; publication errors poison and never return Completion."""
    def __init__(self, root, packet, specification, limits, index, locks):
        self.root = Path(root).absolute()
        self.root.mkdir(exist_ok=False)
        self.context = (packet, specification, limits, index, tuple(locks))
        self.key = science.request_key(*self.context)
        self.implementation = implementation_identity()
        self.owner = (os.getpid(), threading.get_ident())
        self.guard = threading.Lock()
        self.started = self.poisoned = self.complete = False
        self.intent_pin = io.write_metadata(self.root/'intent.json', _intent(self.key))

    def _check(self):
        if self.owner != (os.getpid(), threading.get_ident()): raise ValueError('stage owner differs')
        if (implementation_identity() != self.implementation or science.request_key(*self.context) != self.key
                or io.digest(io.read_stable(self.root/'intent.json', io.META_CAP)[0]) != self.intent_pin):
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
            producer = capture.StageCapture(self.root/'capture', request_sha256=self.key,
                expected_structure=capture.old.audit._structure(model),
                expected_implementation=capture.implementation_identity())
            def callback(raw, results, actual_model):
                return science.consume(producer.root/'science', producer.raw.root/'000/raw.bin',
                    results, actual_model, *self.context, expected_native_sha=io.digest(raw),
                    expected_binding=producer.binding_sha, expected_export=producer.records['export.json'])
            answer = producer.run(lambda: model, specification, callback)
            if (producer.complete is not True or producer.poisoned is not False or
                    producer.owner != self.owner or producer.guard.locked()):
                raise ValueError('owned producer did not complete')
            self._check()
            complete_pin = io.digest(io.read_stable(producer.root/'complete.json', io.META_CAP)[0])
            science_pin = answer['terminal_sha256']
            with science.prior.guard.solver_calls_forbidden():
                _, view_pin, _, views = _records(self.root, *self.context,
                    complete_pin=complete_pin, science_pin=science_pin, handshake=False)
                pin = io.write_metadata(self.root/'handshake.json', _handshake(self.key, complete_pin, science_pin, view_pin))
                inspect(self.root, *self.context, expected_handshake_sha=pin)
                # Publication may not replace the source snapshot with a new one.
                _unchanged(self.root, _layout(self.root, handshake=True), views, handshake=True)
            self._check()
            receipt = Completion(self.root, pin, complete_pin, science_pin, _token=_TOKEN)
            self.complete = True
            return receipt
        except BaseException:
            self.poisoned = True
            raise
        finally:
            self.guard.release()
