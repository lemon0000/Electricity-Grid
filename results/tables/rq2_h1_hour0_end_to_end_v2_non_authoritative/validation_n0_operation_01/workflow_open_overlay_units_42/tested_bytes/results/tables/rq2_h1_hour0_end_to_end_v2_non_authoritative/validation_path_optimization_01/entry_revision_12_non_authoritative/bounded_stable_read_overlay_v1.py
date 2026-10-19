"""Draft two-stage Path.open overlay; the enclosing byte lease stays sole owner.

Install before importing the static byte-lease module, bind after byte enter,
quiesce before byte exit, and restore Path.open after byte cleanup. Every raw
stat/open/fstat/read/fstat/path observation remains fresh. No data are cached.
"""
from contextlib import contextmanager
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import sys
from threading import get_ident
from types import CodeType, FunctionType, SimpleNamespace

from experiments import h1_raw_ingress_development_v1 as raw


SCHEMA = 'h1_bounded_stable_read_overlay_draft_v1'
RAW_SHA256 = 'df59ba543655307f0aae369bebf85e46d5ed94a3525f1a7f72f718fe744b598a'
BYTE_MODULE = 'performance.static_scientific_input_read_lease_v2'


def _state(fn):
    return (fn.__code__, id(fn.__defaults__), repr(fn.__defaults__),
            id(fn.__kwdefaults__), repr(fn.__kwdefaults__),
            tuple(id(c.cell_contents) for c in fn.__closure__ or ())) if type(fn) is FunctionType else None


def _describe(error):
    try: return repr(error)
    except BaseException: return '<exception repr failed>'


def operation():
    """Return install/bind contexts and a detached terminal reader; no OS owner."""
    _RUNTIME()
    source = Path(raw.__file__)
    source_bytes = source.read_bytes()
    if sha256(source_bytes).hexdigest() != RAW_SHA256:
        raise ValueError('canonical raw-reader source pin required')
    compiled = compile(source_bytes, str(source), 'exec')
    for name in ('read_stable', 'identity'):
        fn = getattr(raw, name)
        body, = [c for c in compiled.co_consts if type(c) is CodeType and c.co_name == name]
        if (type(fn) is not FunctionType or fn.__globals__ is not vars(raw) or
                fn.__code__.co_filename != str(source) or fn.__code__ != body):
            raise ValueError('source-authored raw-reader functions required')
    creator = (os.getpid(), get_ident())
    original_open, original_bytes, original_io = Path.open, Path.read_bytes, io.open
    open_state, bytes_state = _state(original_open), _state(original_bytes)
    own = sha256(Path(__file__).read_bytes()).hexdigest()
    frame_of, get_trace, get_profile = sys._getframe, sys.gettrace, sys.getprofile
    raw_fn, raw_code, raw_globals = raw.read_stable, raw.read_stable.__code__, vars(raw)
    fixed = tuple((obj, name, getattr(obj, name), _state(getattr(obj, name))) for obj, names in (
        (raw, ('read_stable', 'identity', 'os', 'stat', 'Path')),
        (os, ('fstat', 'getpid')), (Path, ('stat',)), (raw.stat, ('S_ISREG',))) for name in names)
    streams = {}
    # These containers must keep their identities: the byte module will capture
    # the wrapper's closure before bind fills in its owner and phase.
    state = dict(phase='new', owner=None, first_failure=None, receipt=None, opening=False,
                 calls=0, hits=0, fallback=0, original_requested_bytes=0,
                 bounded_requested_bytes=0, closed_streams=0, cleanup_errors=[])
    bound = {}
    proxy_states = ()

    def fail(error):
        if state['first_failure'] is None: state['first_failure'] = _describe(error)

    def check(*, target=False):
        _RUNTIME()
        if (state['phase'] not in ('installed', 'bound', 'quiesced') or Path.open is not opening or
                _state(opening) != opening_state or io.open is not original_io or
                _state(original_open) != open_state or _state(original_bytes) != bytes_state or
                sys._getframe is not frame_of or sys.gettrace is not get_trace or sys.getprofile is not get_profile or
                any(getattr(obj, name) is not value or _state(value) != before for obj, name, value, before in fixed) or
                any(vars(Proxy).get(name) is not fn or _state(fn) != before for name, fn, before in proxy_states)):
            raise ValueError('bounded read overlay route changed')
        if target:
            if state['first_failure'] is not None: raise ValueError('bounded read overlay poisoned')
            if (state['phase'] != 'bound' or creator != (os.getpid(), get_ident()) or
                    get_trace() is not None or get_profile() is not None):
                raise ValueError('bound untraced creating-thread raw reader required')
            owner = state['owner']
            if (type(owner) is not bound['kind'] or sys.modules.get(BYTE_MODULE) is not bound['module'] or
                    bound['module'].StaticScientificInputReadLease is not bound['kind'] or
                    owner._state != 'active' or Path.read_bytes is not bound['reader'] or
                    owner._expected is not bound['expected'] or owner._expected.get(source) != RAW_SHA256 or
                    owner._files.get(source) != bound['source_handle'] or
                    any(vars(obj).get(name) is not fn or _state(fn) != before
                        for obj, name, fn, before in bound['methods'])):
                raise ValueError('original sole byte owner required')
            bound['light'](owner)
            bound['control'](owner)

    def forget(row):
        if row['stream'].closed:
            streams.pop(id(row['proxy']), None)
            state['closed_streams'] += 1
            return True
        return False

    def drain():
        errors = []
        for row in tuple(streams.values()):
            try: row['close']()
            except BaseException as error: errors.append(error)
            try:
                if not forget(row): errors.append(ValueError('raw stream remains open'))
            except BaseException as error: errors.append(error)
        return errors

    def row_for(proxy):
        try:
            row = streams.get(id(proxy))
            if row is None or row['proxy'] is not proxy: raise ValueError('original active raw stream required')
            check(target=True)
            return row
        except BaseException as error:
            fail(error)
            raise

    class Proxy:
        __slots__ = ()
        def __enter__(self):
            row = row_for(self)
            try:
                if row['stage'] != 'opened': raise ValueError('raw stream enter order changed')
                row['reader'] = row['stream'].__enter__()
                row['stage'] = 'entered'
                return self
            except BaseException as error:
                fail(error)
                try: row['close']()
                except BaseException as cleanup: error.add_note('raw stream enter cleanup: '+_describe(cleanup))
                finally: forget(row)
                raise
        def fileno(self):
            row = row_for(self)
            try:
                if row['stage'] not in ('entered', 'read'): raise ValueError('raw fileno order changed')
                result = row['reader'].fileno()
                row['stage'] = 'first_fileno' if row['stage'] == 'entered' else 'second_fileno'
                return result
            except BaseException as error:
                fail(error)
                raise
        def read(self, n=-1):
            row = row_for(self)
            try:
                if row['stage'] != 'first_fileno' or type(n) is not int or n != row['original_n']:
                    raise ValueError('exact canonical raw read length/order required')
                state['original_requested_bytes'] += n
                state['bounded_requested_bytes'] += row['bounded_n']
                result = row['reader'].read(row['bounded_n'])
                row['stage'] = 'read'
                state['hits'] += 1
                return result
            except BaseException as error:
                fail(error)
                raise
        def __exit__(self, kind, error, tb):
            row = streams.get(id(self))
            if row is None or row['proxy'] is not self: raise ValueError('original raw exit stream required')
            guard = None
            try:
                check(target=True)
                if error is None and row['stage'] != 'second_fileno':
                    raise ValueError('incomplete raw read at exit')
            except BaseException as secondary: guard = secondary; fail(secondary)
            try:
                return row['stream'].__exit__(kind, error, tb)
            except BaseException as secondary:
                fail(secondary)
                if error is not None:
                    error.add_note('raw stream exit: '+_describe(secondary))
                    return False
                raise
            finally:
                forget(row)
                if guard is not None:
                    if error is not None: error.add_note('raw stream guard: '+_describe(guard))
                    else: raise guard

    def opening(path, *args, **kwargs):
        frame = frame_of(1)
        target = frame.f_code is raw_code
        try:
            check(target=target)
            if not target:
                state['fallback'] += 1
                return original_open(path, *args, **kwargs)
            if frame.f_globals is not raw_globals:
                raise ValueError('canonical raw code with foreign globals refused')
            if state['opening'] or streams: raise ValueError('raw read overlay is nonreentrant')
            before, cap = frame.f_locals.get('before'), frame.f_locals.get('cap')
            if (frame.f_locals.get('path') is not path or args != ('rb',) or kwargs or
                    type(before) is not tuple or len(before) != 5 or any(type(v) is not int for v in before) or
                    type(cap) is not int or not 0 <= before[2] <= cap <= sys.maxsize-1):
                raise ValueError('exact canonical raw open contract required')
            state['calls'] += 1
            state['opening'] = True
            try:
                stream = original_open(path, *args, **kwargs)
                proxy = Proxy()
                streams[id(proxy)] = dict(proxy=proxy, stream=stream, reader=stream, close=stream.close,
                    stage='opened', original_n=cap+1, bounded_n=before[2]+1)
                return proxy
            finally: state['opening'] = False
        except BaseException as error:
            fail(error)
            raise
        finally: del frame

    opening_state = _state(opening)
    proxy_states = tuple((name, fn, _state(fn)) for name, fn in vars(Proxy).items() if type(fn) is FunctionType)

    @contextmanager
    def bind(owner):
        primary = None
        try:
            check()
            module = sys.modules.get(BYTE_MODULE)
            kind = getattr(module, 'StaticScientificInputReadLease', None)
            if (state['phase'] != 'installed' or type(owner) is not kind or owner._state != 'active' or
                    source not in owner._files or owner._expected.get(source) != RAW_SHA256):
                raise TypeError('one exact live static byte owner with held raw source required')
            module._RUNTIME()
            owner._check_hooks()
            base = kind.__bases__[0]
            methods = tuple((obj, name, vars(obj)[name], _state(vars(obj)[name])) for obj, names in (
                (kind, ('_check_control', '_check_hooks', 'closed_receipt')),
                (base, ('_check_hooks',))) for name in names)
            bound.update(module=module, kind=kind, reader=Path.read_bytes, expected=owner._expected,
                         source_handle=owner._files[source], light=base._check_hooks, control=kind._check_control,
                         methods=methods, closed_reader=kind.closed_receipt)
            state.update(owner=owner, phase='bound')
            check(target=True)
            yield
            check(target=True)
        except BaseException as error:
            primary = error; fail(error)
            raise
        finally:
            errors = drain()
            state['phase'] = 'quiesced'
            for error in errors: fail(error)
            state['cleanup_errors'].extend(_describe(e) for e in errors)
            if errors:
                if primary is not None:
                    for error in errors: primary.add_note('raw bind cleanup: '+_describe(error))
                else: raise errors[0]

    @contextmanager
    def install():
        primary = None
        try:
            if (creator != (os.getpid(), get_ident()) or state['phase'] != 'new' or
                    BYTE_MODULE in sys.modules or Path.open is not original_open or Path.read_bytes is not original_bytes):
                raise ValueError('install once before loading the byte module')
            state['phase'] = 'installed'
            Path.open = opening
            check()
            yield
        except BaseException as error:
            primary = error; fail(error)
            raise
        finally:
            errors = drain()
            byte_facts = None
            try:
                check()
                if state['owner'] is None: raise ValueError('no byte owner was bound')
                bound['module']._RUNTIME()
                byte_facts = bound['closed_reader'](state['owner'])
                if (state['phase'] != 'quiesced' or byte_facts['state'] != 'closed' or
                        not byte_facts['all_handles_closed'] or not byte_facts['original_alias_restored'] or
                        not byte_facts['exit_files_and_ancestors_verified'] or
                        byte_facts['first_failure'] is not None or byte_facts['cleanup_errors'] or
                        Path.read_bytes is not original_bytes):
                    raise ValueError('byte owner did not close cleanly before open restoration')
            except BaseException as error: errors.append(error)
            restored = False
            if Path.open is opening or Path.open is original_open:
                try:
                    type.__setattr__(Path, 'open', original_open)
                    restored = Path.open is original_open
                except BaseException as error: errors.append(error)
            else: errors.append(ValueError('foreign Path.open preserved'))
            for error in errors: fail(error)
            state['cleanup_errors'].extend(_describe(e) for e in errors)
            state['phase'] = 'closed'
            state['receipt'] = json.dumps(dict(schema=SCHEMA, implementation=own, raw_source_sha256=RAW_SHA256,
                original_open_restored=restored, original_read_bytes_restored=Path.read_bytes is original_bytes,
                remaining_streams=len(streams), first_failure=state['first_failure'], cleanup_errors=state['cleanup_errors'],
                byte_owner_closed_receipt=byte_facts, original_read_calls=state['calls'], bounded_read_calls=state['hits'],
                fallback_opens=state['fallback'], original_requested_bytes=state['original_requested_bytes'],
                bounded_requested_bytes=state['bounded_requested_bytes'], closed_streams=state['closed_streams'],
                source_or_result_cache=False, numerical_result_cache=False, saved_record_cache=False,
                owns_OS_handles=False, audit_hook_transparency_proven=False, per_site_IO_failure_order_preserved=False,
                formal_result=False, resource_admission=False), sort_keys=True)
            if errors:
                if primary is not None:
                    for error in errors: primary.add_note('raw overlay cleanup: '+_describe(error))
                else: raise errors[0]

    def receipt():
        _RUNTIME()
        if creator != (os.getpid(), get_ident()) or state['phase'] != 'closed':
            raise ValueError('closed creating-thread overlay required')
        return json.loads(state['receipt'])
    return SimpleNamespace(install=install, bind=bind, closed_receipt=receipt)


def _install_runtime():
    namespace, module = globals(), sys.modules[__name__]
    rows = tuple((n, v, _state(v)) for n, v in namespace.items() if not n.startswith('__'))
    names = frozenset(n for n, _, _ in rows) | {'_RUNTIME'}
    def check():
        if (sys.modules.get(module.__name__) is not module or namespace.get('_RUNTIME') is not check or
                frozenset(n for n in namespace if not n.startswith('__')) != names or
                any(namespace.get(n) is not v or _state(v) != before for n, v, before in rows)):
            raise ValueError('bounded read overlay helper changed')
    return check


_RUNTIME = _install_runtime()
