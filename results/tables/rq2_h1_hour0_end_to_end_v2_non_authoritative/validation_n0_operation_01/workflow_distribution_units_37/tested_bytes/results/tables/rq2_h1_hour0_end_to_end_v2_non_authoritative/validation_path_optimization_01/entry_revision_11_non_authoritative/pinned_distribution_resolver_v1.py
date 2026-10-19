"""Draft path reuse for eight locked distribution metadata inputs.

Only discovery paths are reused; every call gets a fresh PathDistribution.
The enclosing MetadataParseLease owns all OS resources and version parsing.
Unknown names, subclasses and changed discovery environments use the original
resolver. Entry/exit discovery oracles are explicit; transient ABA is unproved.
"""
from contextlib import contextmanager
from hashlib import sha256
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import sys
from threading import get_ident
from types import CodeType, FunctionType, MethodType

from performance.metadata_parse_lease import MetadataParseLease


SCHEMA = 'h1_pinned_distribution_resolver_draft_v1'
NAMES = ('Pyomo', 'highspy', 'numpy', 'scipy', 'PYPOWER', 'PyYAML', 'osqp', 'gurobipy')


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def _state(value):
    if type(value) is MethodType:
        return (value.__func__, id(value.__self__), _state(value.__func__))
    if isinstance(value, (classmethod, staticmethod)):
        return (value, _state(value.__func__))
    if isinstance(value, property):
        return tuple(_state(x) for x in (value.fget, value.fset, value.fdel))
    if type(value) is FunctionType:
        return (value.__code__, id(value.__defaults__), repr(value.__defaults__),
                id(value.__kwdefaults__), repr(value.__kwdefaults__),
                tuple(id(c.cell_contents) for c in value.__closure__ or ()))
    wrapped = getattr(value, '__wrapped__', None)
    return (wrapped, _state(wrapped)) if wrapped is not None else None


def _authored(fn, qualname):
    path = Path(metadata.__file__)
    if (type(fn) is not FunctionType or fn.__globals__ is not vars(metadata) or
            fn.__module__ != 'importlib.metadata' or fn.__qualname__ != qualname or
            fn.__code__.co_filename != str(path)):
        raise ValueError('canonical metadata function provenance required')
    def find(code):
        if code.co_qualname == qualname: return code
        for value in code.co_consts:
            if type(value) is CodeType:
                result = find(value)
                if result is not None: return result
        return None
    if fn.__code__ != find(compile(path.read_bytes(), str(path), 'exec')):
        raise ValueError('source-authored metadata body required')


def implementation_identity():
    return sha256(Path(__file__).read_bytes()).hexdigest()


def operation(owner, expected):
    """One creator-thread resolver scope inside an exact live parse lease."""
    _RUNTIME()
    if type(owner) is not MetadataParseLease or owner._state != 'active':
        raise TypeError('exact live MetadataParseLease required')
    expected = {Path(p): pin for p, pin in expected.items()}
    if len(expected) != 8 or expected != owner._expected:
        raise ValueError('exact eight held METADATA declarations required')
    owner._check()
    cls = metadata.Distribution
    original = vars(cls)['from_name']
    if type(original) is not classmethod:
        raise TypeError('original metadata classmethod required')
    for fn, name in ((original.__func__, 'Distribution.from_name'),
                     (metadata.version, 'version'), (metadata.distribution, 'distribution')):
        _authored(fn, name)
    creator = (os.getpid(), get_ident())
    own = implementation_identity()
    code_pin = sha256(Path(metadata.__file__).read_bytes()).hexdigest()
    # Fixed parser ownership fields. The legitimate discovery-window method can
    # change _paths/_finders and clear _values without changing held inputs.
    owned = tuple((name, getattr(owner, name)) for name in
        ('_expected', '_raw', '_files', '_identities', '_handles', '_property', '_original'))
    raw = tuple(owner._raw.items())
    files, identities, handles = dict(owner._files), dict(owner._identities), tuple(owner._handles)
    bindings = tuple((obj, name, getattr(obj, name), _state(getattr(obj, name))) for obj, names in (
        (metadata, ('Distribution', 'PathDistribution', 'version', 'distribution')),
        (metadata.Distribution, ('version',)),
        (metadata.PathDistribution, ('__init__', 'read_text', 'locate_file')),
        (MetadataParseLease, ('_check', 'begin_discovery_window')))
        for name in names)
    finder_rows = []
    for kind, names in ((metadata.Distribution, ('discover', '_discover_resolvers')),
        (metadata.MetadataPathFinder, ('find_distributions', '_search_paths')),
        (metadata.Prepared, tuple(n for n in vars(metadata.Prepared) if not n.startswith('__'))+('__new__', '__init__')),
        (metadata.FastPath, tuple(n for n in vars(metadata.FastPath) if not n.startswith('__'))+('__new__', '__init__'))):
        for name in names:
            value = vars(kind).get(name)
            finder_rows.append((kind, name, value, _state(value)))
    data = {}
    status = dict(phase='new', descriptor=None, descriptor_state=None, first_failure=None,
        calls=0, fast=0, fallback=0, fresh_objects=0, oracles=dict(entry=0, exit=0),
        cleanup_errors=[], receipt=None)
    entry_paths = tuple(sys.path)
    def distribution_finders():
        # Native Distribution._discover_resolvers ignores import-only finders.
        rows = []
        for finder in sys.meta_path:
            method = getattr(finder, 'find_distributions', None)
            if method is not None:
                rows.append((finder, getattr(method, '__func__', method),
                             getattr(method, '__self__', None), _state(method)))
        return tuple(rows)
    entry_finders = distribution_finders()

    def creating():
        if creator != (os.getpid(), get_ident()):
            raise ValueError('metadata resolver creating process/thread required')

    def failure(error):
        if status['first_failure'] is None: status['first_failure'] = repr(error)

    def controls():
        _RUNTIME()
        if status['phase'] == 'closed':
            raise ValueError('live metadata resolver required')
        if (owner._state != 'active' or any(getattr(owner, n) is not v for n, v in owned) or
                owner._expected != expected or owner._files != files or owner._identities != identities or
                tuple(owner._handles) != handles or any(owner._raw.get(k) is not v for k, v in raw)):
            raise ValueError('metadata resolver held parser ownership changed')
        if any(getattr(obj, n) is not v or _state(v) != before for obj, n, v, before in bindings):
            raise ValueError('metadata resolver parser or constructor changed')
        if status['first_failure'] is not None:
            raise ValueError('metadata resolver poisoned')
        if status['phase'] == 'active' and (vars(cls).get('from_name') is not status['descriptor'] or
                _state(status['descriptor']) != status['descriptor_state']):
            raise ValueError('metadata resolver descriptor changed')
        for key, version in owner._values.items():
            if key in data.get('versions_by_path', {}) and version != data['versions_by_path'][key]:
                raise ValueError('metadata resolver cached parsed version changed')

    def stock_graph():
        return (tuple(sys.path) == entry_paths and distribution_finders() == entry_finders and
            all(vars(kind).get(name) is value and _state(value) == before
                for kind, name, value, before in finder_rows))

    def discover(stage):
        controls()
        result = {}
        for name in NAMES:
            found = original.__get__(None, cls)(name)
            all_found = tuple(cls.discover(name=name))
            path = getattr(found, '_path', None)
            if (type(found) is not metadata.PathDistribution or type(path) is not type(Path()) or
                    len(all_found) != 1 or type(all_found[0]) is not metadata.PathDistribution or
                    str(getattr(all_found[0], '_path', None)) != str(path) or path/'METADATA' not in expected):
                raise ValueError('unique canonical held distribution path required: '+name)
            file = path/'METADATA'
            info = file.stat(follow_symlinks=False)
            version = found.version
            if (info.st_file_attributes & 0x400 or info.st_nlink != 1 or
                    (info.st_dev, info.st_ino) != identities[file] or type(version) is not str or not version):
                raise ValueError('held metadata identity/version differs: '+name)
            result[name] = dict(path=str(path), identity=(info.st_dev, info.st_ino),
                                sha256=expected[file], version=version)
        if len({v['path'] for v in result.values()}) != 8:
            raise ValueError('eight disjoint selected distributions required')
        controls()
        status['oracles'][stage] += 1
        return result

    @contextmanager
    def scope():
        creating()
        if status['phase'] != 'new': raise ValueError('single-use metadata resolver required')
        primary = None
        baseline = None
        restored = False
        try:
            controls()
            baseline = discover('entry')
            data['paths'] = {k: v['path'] for k, v in baseline.items()}
            data['versions_by_path'] = {os.path.normcase(str(Path(v['path'])/'METADATA')): v['version']
                                        for v in baseline.values()}
            def route(requested_cls, name):
                creating()
                try:
                    controls()
                    status['calls'] += 1
                    fast = requested_cls is cls and type(name) is str and name in NAMES and stock_graph()
                    if fast:
                        # No mutable Distribution or Path instance is shared.
                        value = metadata.PathDistribution(Path(data['paths'][name]))
                        if type(value) is not metadata.PathDistribution or str(value._path) != data['paths'][name]:
                            raise ValueError('fresh exact selected PathDistribution required')
                        controls()
                        status['fast'] += 1; status['fresh_objects'] += 1
                        return value
                except BaseException as error:
                    failure(error)
                    raise
                status['fallback'] += 1
                return original.__get__(None, requested_cls)(name)
            status.update(phase='active', descriptor=classmethod(route))
            status['descriptor_state'] = _state(status['descriptor'])
            if vars(cls)['from_name'] is not original: raise ValueError('foreign metadata descriptor before install')
            setattr(cls, 'from_name', status['descriptor'])
            controls()
            yield
            controls()
        except BaseException as error:
            primary = error; failure(error)
            raise
        finally:
            status['phase'] = 'closing'
            if vars(cls).get('from_name') is status['descriptor'] or vars(cls).get('from_name') is original:
                try:
                    type.__setattr__(cls, 'from_name', original)
                    restored = vars(cls).get('from_name') is original
                except BaseException as error: status['cleanup_errors'].append(error)
            else: status['cleanup_errors'].append(ValueError('foreign metadata descriptor preserved'))
            if restored and baseline is not None:
                try:
                    if discover('exit') != baseline: raise ValueError('metadata discovery changed across scope')
                    if sha256(Path(metadata.__file__).read_bytes()).hexdigest() != code_pin:
                        raise ValueError('metadata defining source changed')
                except BaseException as error: status['cleanup_errors'].append(error)
            data.clear()
            if status['first_failure'] is None and status['cleanup_errors']:
                failure(status['cleanup_errors'][0])
            status.update(phase='closed', descriptor=None, descriptor_state=None)
            status['receipt'] = _encode(dict(schema=SCHEMA, implementation=own,
                declared_metadata_sha256={str(p): pin for p, pin in expected.items()}, selected=baseline,
                from_name_calls=status['calls'], fast_path_calls=status['fast'], fallback_calls=status['fallback'],
                fresh_PathDistribution_instances=status['fresh_objects'], original_discovery_oracles=status['oracles'],
                original_alias_restored=restored, all_resolver_cached_paths_cleared=not data,
                first_failure=status['first_failure'], cleanup_errors=[repr(e) for e in status['cleanup_errors']],
                distribution_discovery_cached=True, metadata_paths_cached=True, distribution_instances_cached=False,
                native_version_function_unchanged=True, per_call_discovery_preserved=False,
                failure_timing_preserved=False, transient_discovery_ABA_covered=False,
                import_only_finders_ignored_as_in_native_discovery=True,
                outer_MetadataParseLease_cleanup_proven=False, owns_OS_handles=False,
                numerical_result_cache=False, solver_result_cache=False, saved_record_cache=False,
                formal_result=False, resource_admission=False, native_execution_authorized=False))
            if status['cleanup_errors']:
                if primary is not None:
                    for error in status['cleanup_errors']: primary.add_note('metadata resolver cleanup: '+repr(error))
                else: raise status['cleanup_errors'][0]

    def receipt():
        _RUNTIME(); creating()
        if status['phase'] != 'closed' or status['receipt'] is None:
            raise ValueError('closed metadata resolver required')
        return json.loads(status['receipt'])
    return scope(), receipt


def _install_runtime():
    namespace = globals()
    module = sys.modules[__name__]
    rows = tuple((n, v, _state(v)) for n, v in namespace.items() if not n.startswith('__'))
    names = frozenset(n for n, _, _ in rows) | {'_RUNTIME'}
    def check():
        if (sys.modules.get(module.__name__) is not module or namespace.get('_RUNTIME') is not check or
                frozenset(n for n in namespace if not n.startswith('__')) != names or
                any(namespace.get(n) is not v or _state(v) != before for n, v, before in rows)):
            raise ValueError('metadata resolver helper changed')
    return check


_RUNTIME = _install_runtime()
