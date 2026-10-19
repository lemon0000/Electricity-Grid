"""Draft two-stage Path.open overlay; the enclosing byte lease stays sole owner.

Install before importing the static byte-lease module, bind after byte enter,
quiesce before byte exit, and restore Path.open after byte cleanup. Every raw
stat/open/fstat/read/fstat/path observation remains fresh. No data are cached.
"""
from contextlib import contextmanager
import dis
from hashlib import sha256
from importlib.machinery import ModuleSpec, SourceFileLoader
import io
import json
import os
from pathlib import Path
import pathlib
import sys
from threading import get_ident
from types import BuiltinFunctionType, CellType, CodeType, FunctionType, MappingProxyType, SimpleNamespace

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


def _note(error, message):
    try: BaseException.add_note(error, message)
    except BaseException: pass


def _freeze(functions):
    signatures, globals_rows, seen, keys = [], [], set(), set()
    def names(code):
        result = {i.argval for i in dis.get_instructions(code) if i.opname == 'LOAD_GLOBAL'}
        for const in code.co_consts:
            if type(const) is CodeType: result.update(names(const))
        return result
    def visit(fn):
        if type(fn) is not FunctionType or id(fn) in seen: return
        seen.add(id(fn))
        cells = tuple(id(c.cell_contents) for c in fn.__closure__ or ())
        signatures.append((fn, fn.__code__, fn.__globals__, fn.__defaults__, fn.__kwdefaults__, cells,
                           repr(fn.__defaults__), repr(fn.__kwdefaults__)))
        for cell in fn.__closure__ or (): visit(cell.cell_contents)
        visit(getattr(fn, '__wrapped__', None))
        namespace = fn.__globals__
        for name in names(fn.__code__) | {'__builtins__'}:
            for mapping in (namespace, fn.__builtins__) if name not in namespace else (namespace,):
                key = (id(mapping), name)
                if key in keys: continue
                keys.add(key)
                value = mapping.get(name)
                globals_rows.append((mapping, name, name in mapping, value))
                if type(value) is FunctionType and value.__module__ in (__name__, raw.__name__): visit(value)
    for fn in functions: visit(fn)
    return tuple(signatures), tuple(globals_rows)


def _verify(signatures, globals_rows):
    # Cloned with independent globals, code anchor and captured closure values.
    # Do not dispatch through _state or other mutable local checker functions.
    for fn, code, namespace, defaults, keywords, cells, dr, kr in signatures:
        if (fn.__code__ is not code or fn.__globals__ is not namespace or fn.__defaults__ is not defaults or
                fn.__kwdefaults__ is not keywords or repr(fn.__defaults__) != dr or repr(fn.__kwdefaults__) != kr or
                tuple(id(c.cell_contents) for c in fn.__closure__ or ()) != cells):
            raise ValueError('bounded overlay function closure changed')
    for mapping, name, present, value in globals_rows:
        if (name in mapping) != present or mapping.get(name) is not value:
            raise ValueError('bounded overlay direct global or builtin shadow changed')


def _authored(fn, module, qualname):
    def find(code):
        if code.co_qualname == qualname: return code
        for const in code.co_consts:
            if type(const) is CodeType:
                result = find(const)
                if result is not None: return result
        return None
    path = Path(module.__file__)
    return (type(fn) is FunctionType and fn.__globals__ is vars(module) and fn.__module__ == module.__name__ and
            fn.__qualname__ == qualname and fn.__code__.co_filename == str(path) and
            fn.__code__ == find(compile(path.read_bytes(), str(path), 'exec')))


def operation(*, root):
    """Return install/bind contexts and a detached terminal reader; no OS owner."""
    _RUNTIME()
    root = Path(root)
    source = root/'experiments'/'h1_raw_ingress_development_v1.py'
    package = sys.modules.get('experiments')
    if (not root.is_absolute() or '..' in root.parts or sys.modules.get('experiments.h1_raw_ingress_development_v1') is not raw or
            raw.__name__ != 'experiments.h1_raw_ingress_development_v1' or raw.__package__ != 'experiments' or
            raw.__file__ != str(source) or type(raw.__spec__) is not ModuleSpec or
            raw.__spec__.name != raw.__name__ or raw.__spec__.origin != str(source) or
            type(raw.__loader__) is not SourceFileLoader or raw.__spec__.loader is not raw.__loader__ or
            raw.__loader__.name != raw.__name__ or raw.__loader__.path != str(source) or
            getattr(package, 'h1_raw_ingress_development_v1', None) is not raw or
            package.__file__ != str(root/'experiments'/'__init__.py')):
        raise ValueError('exact canonical raw module registry and repository provenance required')
    source_bytes = source.read_bytes()
    if sha256(source_bytes).hexdigest() != RAW_SHA256:
        raise ValueError('canonical raw-reader source pin required')
    compiled = compile(source_bytes, str(source), 'exec')
    for name in ('read_stable', 'identity'):
        fn = getattr(raw, name)
        body, = [c for c in compiled.co_consts if type(c) is CodeType and c.co_name == name]
        if (type(fn) is not FunctionType or fn.__globals__ is not vars(raw) or fn.__module__ != raw.__name__ or
                fn.__qualname__ != name or
                fn.__code__.co_filename != str(source) or fn.__code__ != body):
            raise ValueError('source-authored raw-reader functions required')
    creator = (os.getpid(), get_ident())
    original_open, original_bytes, original_io = Path.open, Path.read_bytes, io.open
    open_state, bytes_state = _state(original_open), _state(original_bytes)
    own = sha256(Path(__file__).read_bytes()).hexdigest()
    canonical_io = (all(_authored(fn, pathlib, name) for fn, name in
        ((original_open, 'Path.open'), (original_bytes, 'Path.read_bytes'), (Path.stat, 'Path.stat'))) and
        original_open.__defaults__ == ('r', -1, None, None, None) and original_open.__kwdefaults__ is None and
        original_bytes.__defaults__ is None and original_bytes.__kwdefaults__ is None and
        Path.stat.__defaults__ is None and Path.stat.__kwdefaults__ == {'follow_symlinks': True} and
        pathlib.io is io and type(io.open) is BuiltinFunctionType and io.open.__name__ == 'open' and
        type(os.fstat) is BuiltinFunctionType and os.fstat.__module__ == 'nt' and os.fstat.__name__ == 'fstat' and
        type(os.stat) is BuiltinFunctionType and os.stat.__module__ == 'nt' and os.stat.__name__ == 'stat' and
        type(raw.stat.S_ISREG) is BuiltinFunctionType and raw.stat.S_ISREG.__name__ == 'S_ISREG')
    frame_of, get_trace, get_profile = sys._getframe, sys.gettrace, sys.getprofile
    raw_fn, raw_code, raw_globals = raw.read_stable, raw.read_stable.__code__, vars(raw)
    fixed = tuple((obj, name, getattr(obj, name), _state(getattr(obj, name))) for obj, names in (
        (raw, ('read_stable', 'identity', 'os', 'stat', 'Path')),
        (raw, ('__name__', '__file__', '__spec__', '__loader__', '__package__')),
        (raw.__spec__, ('name', 'origin', 'loader')),
        (raw.__loader__, ('name', 'path')),
        (package, ('h1_raw_ingress_development_v1', '__file__')),
        (pathlib, ('io',)), (io, ('text_encoding',)),
        (os, ('stat', 'fstat', 'getpid')), (Path, ('stat',)), (raw.stat, ('S_ISREG',))) for name in names)
    streams = {}
    error_repr = BaseException.__repr__
    # These containers must keep their identities: the byte module will capture
    # the wrapper's closure before bind fills in its owner and phase.
    state = dict(phase='new', owner=None, first_failure=None, receipt=None, opening=False,
                 calls=0, hits=0, fallback=0, raw_fallback=0, original_requested_bytes=0,
                 bounded_requested_bytes=0, closed_streams=0, cleanup_errors=[], orphan=None,
                 byte_cleanup_retry_attempted=False)
    bound = {}
    audit_data = {}
    audit = MappingProxyType(audit_data)
    proxy_states = ()
    proxy_keys = None

    def check(*, target=False):
        _RUNTIME()
        if (state['phase'] not in ('installed', 'bound', 'quiesced') or Path.open is not opening or
                _state(opening) != audit['opening_state'] or io.open is not original_io or
                _state(original_open) != open_state or _state(original_bytes) != bytes_state or
                sys._getframe is not frame_of or sys.gettrace is not get_trace or sys.getprofile is not get_profile or
                any(getattr(obj, name) is not value or _state(value) != before for obj, name, value, before in fixed) or
                sys.modules.get(raw.__name__) is not raw or sys.modules.get('experiments') is not package or
                frozenset(vars(Proxy)) != proxy_keys or Proxy.__bases__ != (object,) or
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
        orphan = state['orphan']
        if orphan is not None:
            try: orphan.close()
            except BaseException as error: errors.append(error)
            try:
                if orphan.closed: state['orphan'] = None; state['closed_streams'] += 1
                else: errors.append(ValueError('unregistered raw stream remains open'))
            except BaseException as error: errors.append(error)
        for row in tuple(streams.values()):
            try: row['close']()
            except BaseException as error: errors.append(error)
            try:
                if row['stream'].closed:
                    streams.pop(id(row['proxy']), None)
                    state['closed_streams'] += 1
                else: errors.append(ValueError('raw stream remains open'))
            except BaseException as error: errors.append(error)
        return errors

    def row_for(proxy):
        try:
            if (audit['verifier'].__code__ is not audit['verifier_code'] or
                    audit['verifier'].__globals__.keys() != {'__builtins__'} or
                    audit['verifier'].__globals__.get('__builtins__') is not audit['verifier_builtins']):
                raise ValueError('fixed overlay verifier required')
            audit['verifier'](*audit['records'])
            row = streams.get(id(proxy))
            if row is None or row['proxy'] is not proxy: raise ValueError('original active raw stream required')
            check(target=True)
            return row
        except BaseException as error:
            if state['first_failure'] is None: state['first_failure'] = error_repr(error)
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
                if state['first_failure'] is None: state['first_failure'] = error_repr(error)
                try: row['close']()
                except BaseException as cleanup: _note(error, 'raw stream enter cleanup: '+_describe(cleanup))
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
                if state['first_failure'] is None: state['first_failure'] = error_repr(error)
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
                if state['first_failure'] is None: state['first_failure'] = error_repr(error)
                raise
        def __exit__(self, kind, error, tb):
            row = streams.get(id(self))
            if row is None or row['proxy'] is not self: raise ValueError('original raw exit stream required')
            if error is not None and state['first_failure'] is None: state['first_failure'] = error_repr(error)
            guard = None
            try:
                if (audit['verifier'].__code__ is not audit['verifier_code'] or
                        audit['verifier'].__globals__.keys() != {'__builtins__'} or
                        audit['verifier'].__globals__.get('__builtins__') is not audit['verifier_builtins']):
                    raise ValueError('fixed overlay verifier required')
                audit['verifier'](*audit['records'])
                check(target=True)
                if error is None and row['stage'] != 'second_fileno':
                    raise ValueError('incomplete raw read at exit')
            except BaseException as secondary:
                guard = secondary
                if state['first_failure'] is None: state['first_failure'] = error_repr(secondary)
            try:
                return row['stream'].__exit__(kind, error, tb)
            except BaseException as secondary:
                if state['first_failure'] is None: state['first_failure'] = error_repr(secondary)
                if guard is None: guard = secondary
                else: _note(guard, 'raw stream exit: '+_describe(secondary))
                if error is not None:
                    _note(error, 'raw stream exit: '+_describe(secondary))
                    return False
                raise
            finally:
                try:
                    if not forget(row): raise ValueError('original raw stream did not close at call boundary')
                except BaseException as secondary:
                    if state['first_failure'] is None: state['first_failure'] = error_repr(secondary)
                    if error is not None: _note(error, 'raw stream closure: '+_describe(secondary))
                    elif guard is None: guard = secondary
                    else: _note(guard, 'raw stream closure: '+_describe(secondary))
                if guard is not None:
                    if error is not None: _note(error, 'raw stream guard: '+_describe(guard))
                    else: raise guard

    def opening(path, *args, **kwargs):
        frame = frame_of(1)
        target = frame.f_code is raw_code
        delegating = False
        try:
            if (audit['verifier'].__code__ is not audit['verifier_code'] or
                    audit['verifier'].__globals__.keys() != {'__builtins__'} or
                    audit['verifier'].__globals__.get('__builtins__') is not audit['verifier_builtins']):
                raise ValueError('fixed overlay verifier required')
            audit['verifier'](*audit['records'])
            check(target=target)
            if not target:
                state['fallback'] += 1
                delegating = True
                return original_open(path, *args, **kwargs)
            if frame.f_globals is not raw_globals:
                raise ValueError('canonical raw code with foreign globals refused')
            if state['opening'] or streams: raise ValueError('raw read overlay is nonreentrant')
            before, cap = frame.f_locals.get('before'), frame.f_locals.get('cap')
            if (frame.f_locals.get('path') is not path or args != ('rb',) or kwargs or
                    type(before) is not tuple or len(before) != 5 or any(type(v) is not int for v in before)):
                raise ValueError('exact canonical raw open contract required')
            if type(cap) is not int or not 0 <= before[2] <= cap <= sys.maxsize-1:
                state['fallback'] += 1
                state['raw_fallback'] += 1
                delegating = True
                return original_open(path, *args, **kwargs)
            state['calls'] += 1
            state['opening'] = True
            try:
                stream = original_open(path, *args, **kwargs)
                try:
                    proxy = Proxy()
                    streams[id(proxy)] = dict(proxy=proxy, stream=stream, reader=stream, close=stream.close,
                        stage='opened', original_n=cap+1, bounded_n=before[2]+1)
                    return proxy
                except BaseException as error:
                    # Own the stream even if proxy construction/registration failed.
                    try: stream.close()
                    except BaseException as cleanup:
                        state['orphan'] = stream
                        _note(error, 'unregistered raw stream cleanup: '+_describe(cleanup))
                    finally:
                        if not stream.closed: state['orphan'] = stream
                    raise
            finally: state['opening'] = False
        except BaseException as error:
            if not delegating and state['first_failure'] is None: state['first_failure'] = error_repr(error)
            raise
        finally: del frame

    proxy_states = tuple((name, fn, _state(fn)) for name, fn in vars(Proxy).items() if type(fn) is FunctionType)
    proxy_keys = frozenset(vars(Proxy))

    def adopt(owner):
        # Record the sole owner before its enter can acquire handles and fail.
        # This registration acquires nothing and does not enable target reads.
        check()
        module = sys.modules.get(BYTE_MODULE)
        kind = getattr(module, 'StaticScientificInputReadLease', None)
        if (creator != (os.getpid(), get_ident()) or state['phase'] != 'installed' or
                state['owner'] is not None or type(owner) is not kind or owner._state != 'new' or
                owner._expected.get(source) != RAW_SHA256):
            error = ValueError('register one exact new byte owner before enter')
            if state['first_failure'] is None: state['first_failure'] = error_repr(error)
            raise error
        module._RUNTIME()
        bound.update(module=module, kind=kind, closed_reader=kind.closed_receipt, retry=kind.retry_cleanup)
        state['owner'] = owner

    @contextmanager
    def bind(owner):
        check()
        module = sys.modules.get(BYTE_MODULE)
        kind = getattr(module, 'StaticScientificInputReadLease', None)
        if (state['phase'] != 'installed' or state['owner'] is not owner or
                type(owner) is not kind or owner._state != 'active' or
                source not in owner._files or owner._expected.get(source) != RAW_SHA256):
            error = TypeError('one exact live static byte owner with held raw source required')
            if state['first_failure'] is None: state['first_failure'] = error_repr(error)
            raise error
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
        primary = None
        try:
            check(target=True)
            yield
            if (audit['verifier'].__code__ is not audit['verifier_code'] or
                    audit['verifier'].__globals__.keys() != {'__builtins__'} or
                    audit['verifier'].__globals__.get('__builtins__') is not audit['verifier_builtins']):
                raise ValueError('fixed overlay verifier required')
            audit['verifier'](*audit['records'])
            check(target=True)
        except BaseException as error:
            primary = error
            if state['first_failure'] is None: state['first_failure'] = error_repr(error)
            raise
        finally:
            closer = audit['make'](audit['drain_code'], dict(audit['drain_globals']), 'drain',
                audit['drain_defaults'], tuple(audit['cell'](v) for v in audit['drain_values']))
            errors = closer()
            state['phase'] = 'quiesced'
            for error in errors:
                if state['first_failure'] is None: state['first_failure'] = error_repr(error)
            state['cleanup_errors'].extend(_describe(e) for e in errors)
            if errors:
                if primary is not None:
                    for error in errors: _note(primary, 'raw bind cleanup: '+_describe(error))
                else: raise errors[0]

    @contextmanager
    def install():
        if (creator != (os.getpid(), get_ident()) or state['phase'] != 'new' or
                BYTE_MODULE in sys.modules or Path.open is not original_open or Path.read_bytes is not original_bytes):
            error = ValueError('install once before loading the byte module')
            if state['phase'] in ('installed', 'bound', 'quiesced') and state['first_failure'] is None:
                state['first_failure'] = error_repr(error)
            raise error
        primary = None
        try:
            state['phase'] = 'installed'
            Path.open = opening
            check()
            yield
        except BaseException as error:
            primary = error
            if state['first_failure'] is None: state['first_failure'] = error_repr(error)
            raise
        finally:
            closer = audit['make'](audit['drain_code'], dict(audit['drain_globals']), 'drain',
                audit['drain_defaults'], tuple(audit['cell'](v) for v in audit['drain_values']))
            errors = closer()
            byte_facts = None
            try:
                if (audit['verifier'].__code__ is not audit['verifier_code'] or
                        audit['verifier'].__globals__.keys() != {'__builtins__'} or
                        audit['verifier'].__globals__.get('__builtins__') is not audit['verifier_builtins']):
                    raise ValueError('fixed overlay verifier required')
                audit['verifier'](*audit['records'])
                check()
                if state['owner'] is None: raise ValueError('no byte owner was bound')
                bound['module']._RUNTIME()
                byte_facts = bound['closed_reader'](state['owner'])
                if byte_facts['state'] == 'cleanup_failed' or not byte_facts['all_handles_closed']:
                    # The original retry needs the still-installed Path.open.
                    # Preserve its first error/history; recovery never makes this
                    # attempt clean. There is one bounded retry, no looping.
                    state['byte_cleanup_retry_attempted'] = True
                    bound['retry'](state['owner'])
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
            for error in errors:
                if state['first_failure'] is None: state['first_failure'] = error_repr(error)
            state['cleanup_errors'].extend(_describe(e) for e in errors)
            state['phase'] = 'closed'
            state['receipt'] = json.dumps(dict(schema=SCHEMA, implementation=own, raw_source_sha256=RAW_SHA256,
                raw_module_name=raw.__name__, raw_source_path=str(source), canonical_IO_dependencies=canonical_io,
                eligible_for_canonical_entry_clean=(canonical_io and state['first_failure'] is None and
                    not errors and not streams and state['orphan'] is None and state['calls'] == state['hits']),
                byte_cleanup_retry_attempted=state['byte_cleanup_retry_attempted'],
                original_open_restored=restored, original_read_bytes_restored=Path.read_bytes is original_bytes,
                remaining_streams=len(streams)+(state['orphan'] is not None), first_failure=state['first_failure'], cleanup_errors=state['cleanup_errors'],
                byte_owner_closed_receipt=byte_facts, original_read_calls=state['calls'], bounded_read_calls=state['hits'],
                fallback_opens=state['fallback'], raw_fallback_opens=state['raw_fallback'],
                original_requested_bytes=state['original_requested_bytes'],
                bounded_requested_bytes=state['bounded_requested_bytes'], closed_streams=state['closed_streams'],
                source_or_result_cache=False, numerical_result_cache=False, saved_record_cache=False,
                owns_byte_lease_OS_handles=False, owns_read_stream_lifetimes=True,
                audit_hook_transparency_proven=False, per_site_IO_failure_order_preserved=False,
                transient_dependency_ABA_covered=False,
                formal_result=False, resource_admission=False), sort_keys=True)
            if errors:
                if primary is not None:
                    for error in errors: _note(primary, 'raw overlay cleanup: '+_describe(error))
                else: raise errors[0]

    def receipt():
        _RUNTIME()
        if (audit['verifier'].__code__ is not audit['verifier_code'] or
                audit['verifier'].__globals__.keys() != {'__builtins__'} or
                audit['verifier'].__globals__.get('__builtins__') is not audit['verifier_builtins']):
            raise ValueError('fixed overlay verifier required')
        audit['verifier'](*audit['records'])
        if creator != (os.getpid(), get_ident()) or state['phase'] != 'closed':
            raise ValueError('closed creating-thread overlay required')
        return json.loads(state['receipt'])
    safe_builtins = MappingProxyType(dict(vars(sys.modules['builtins'])))
    audit_data.update(make=FunctionType, cell=CellType,
        verifier=FunctionType(_verify.__code__, {'__builtins__': safe_builtins}), verifier_builtins=safe_builtins,
        verifier_code=_verify.__code__, drain_code=drain.__code__,
        drain_globals=MappingProxyType({'__builtins__': safe_builtins}),
        drain_defaults=drain.__defaults__, drain_values=tuple(c.cell_contents for c in drain.__closure__ or ()))
    audit_data['opening_state'] = _state(opening)
    audit_data['records'] = _freeze((opening, check, forget, row_for, drain, adopt, bind, install, receipt,
        audit['verifier'],
        raw_fn, raw.identity, original_open, original_bytes, *(fn for _, fn, _ in proxy_states)))
    return SimpleNamespace(install=install, adopt=adopt, bind=bind, closed_receipt=receipt)


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
