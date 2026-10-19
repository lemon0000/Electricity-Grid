"""Draft Windows byte transport for code plus two pinned scientific inputs.

This extends the existing code-only OS locking implementation. Scientific
callers still receive the original bytes. No registry, source row, numerical
result, solver result or saved-record object is cached here.
"""
import ctypes
from hashlib import sha256
from pathlib import Path
import stat
import sys
from types import CellType, FunctionType, MappingProxyType

from performance import code_read_lease as base


SCIENTIFIC_INPUTS = (
    ('results/tables/rq2_h1_outage_registry_v1_non_authoritative/'
     'scientific_development_authority.json',
     '45710f18fcf98113d53c50cd74e0dfc311ad3e03cfb8ab8f75b01dc2720de0a8', 888),
    ('results/tables/rq2_h1_outage_origin_replay_v1_non_authoritative/'
     'repair_cap_proposal.json',
     '6435c85b6cc99d243077bd014b1f52cc90427270a4c50cb26a67fb7e34edf031', 23475),
)


def scientific_inputs(root):
    return {str(Path(root)/relative): dict(sha256=pin, size_bytes=size)
            for relative, pin, size in SCIENTIFIC_INPUTS}


def _recipe(fn):
    return (fn.__code__, fn.__globals__, fn.__name__, fn.__defaults__,
            tuple(c.cell_contents for c in fn.__closure__ or ()), dict(fn.__kwdefaults__ or {}))


def _function_signatures(functions):
    return tuple((fn, fn.__code__, fn.__defaults__, fn.__kwdefaults__,
                  tuple(id(c.cell_contents) for c in fn.__closure__ or ()),
                  repr(fn.__defaults__), repr(fn.__kwdefaults__)) for fn in functions)


def _verify_functions(signatures):
    if any(fn.__code__ is not code or fn.__defaults__ is not defaults or
           fn.__kwdefaults__ is not keywords or
           tuple(id(c.cell_contents) for c in fn.__closure__ or ()) != closure or
           repr(fn.__defaults__) != default_repr or repr(fn.__kwdefaults__) != keyword_repr
           for fn, code, defaults, keywords, closure, default_repr, keyword_repr in signatures):
        raise ValueError('ownership capsule function changed')


def _safe_closer(close):
    if isinstance(close, ctypes._CFuncPtr):
        # A separate C function object is immune to errcheck/signature changes
        # on the public kernel binding. Its address and ABI stay the same.
        prototype = ctypes.WINFUNCTYPE(base.wintypes.BOOL, base.wintypes.HANDLE, use_last_error=True)
        return prototype(ctypes.cast(close, ctypes.c_void_p).value)
    # Explicit synthetic API variants are used only by fault tests.
    return close


def _inventory(owner, close_handle):
    """Strong OS ownership independent of mutable diagnostic attributes."""
    opened = []
    pending = set()
    frozen = None
    reader = None
    observations = ()
    win_error, last_error = ctypes.WinError, ctypes.get_last_error
    def track(handle):
        opened.append(handle)
        pending.add(handle)
    def seal():
        nonlocal frozen, reader, observations
        for path, (_, row) in owner._entry.items():
            if not row['directory']:
                row['sha256'] = sha256(owner._data[base._key(path)]).hexdigest()
        observations = tuple((p, h, tuple(row.items())) for p, (h, row) in owner._entry.items())
        owner._handles = tuple(opened)
        owner._files = MappingProxyType(dict(owner._files))
        owner._identities = MappingProxyType(dict(owner._identities))
        owner._entry = MappingProxyType({p: (h, MappingProxyType(dict(row)))
                                        for p, (h, row) in owner._entry.items()})
        frozen = owner._handles, owner._files, owner._identities, owner._entry
        reader = owner._cached_read
    def check():
        if any(current is not expected for current, expected in zip(
                (owner._handles, owner._files, owner._identities, owner._entry), frozen)):
            raise ValueError('owned handle or file/ancestor inventory changed')
    def release():
        failures = []
        for handle in reversed(opened):
            if handle not in pending:
                continue
            try:
                if not close_handle(handle):
                    raise win_error(last_error())
                pending.remove(handle)
            except BaseException as error:
                failures.append(error)
        owner._handles = [h for h in opened if h in pending]
        return failures
    def state():
        return tuple(opened), tuple(h for h in opened if h in pending), observations, reader
    return track, seal, check, release, state


class StaticScientificInputReadLease(base.CodeReadLease):
    """Single-use, process-local read dispatch with separately named inputs."""
    def __init__(self, code_expected, scientific_expected, *, root, code_root,
                 max_files=4096, max_bytes=64*1024**2):
        _RUNTIME()
        if base._key(root) is None or not Path(root).is_relative_to(Path(code_root)):
            raise ValueError('absolute scientific input root required')
        required = scientific_inputs(root)
        # Compare exact declarations, including spelling, before Path folds case.
        if (type(scientific_expected) is not dict or
                {str(p): row for p, row in scientific_expected.items()} != required):
            raise ValueError('exact two scientific input paths, hashes and sizes required')
        super().__init__(code_expected, root=code_root,
                         max_files=max_files-2, max_bytes=max_bytes)
        self._code_paths = self._paths
        self._science = MappingProxyType({Path(p): (row['sha256'], row['size_bytes'])
                                         for p, row in required.items()})
        self._bound_science = self._science
        self._owner_guard = self._guard
        self._path_type = Path
        combined = dict(self._expected)
        if combined.keys() & self._science.keys():
            raise ValueError('disjoint code and scientific inputs required')
        combined.update({p: pin for p, (pin, _) in self._science.items()})
        self._expected = MappingProxyType(combined)
        self._bound_expected = self._expected
        self._paths = tuple(sorted(self._expected, key=str))
        self._bound_paths = self._paths
        self._entry = {}
        self._exit = {}
        self._cleanup_errors = []
        self._first_failure = None
        self._hook_restored = False
        self._foreign_hook_preserved = False
        self._receipt = None
        self._hook_installed = False
        self._capsule = _inventory(self, _safe_closer(base._kernel.CloseHandle))
        self._bound_capsule = self._capsule
        self._capsule_signatures = _function_signatures(self._capsule)
        self._release_recipe = _recipe(self._capsule[3])
        self._state_recipe = _recipe(self._capsule[4])
        self._verify_recipe = _recipe(_verify_functions)
        self._function_type, self._cell_type = FunctionType, CellType
        self._installed_reader = None
        self._code_keys = tuple(base._key(p) for p in self._code_paths)
        self._science_keys = frozenset(base._key(p) for p in self._science)
        self._control = self._bound_control = (
            self._capsule_signatures, self._release_recipe, self._state_recipe, self._verify_recipe,
            FunctionType, CellType, None, self._owner_guard, self._path_type, self._restore_read,
            self._science_keys)
        self.light_code_checks = self.full_scientific_checks = self.full_checkpoint_checks = 0

    @staticmethod
    def _observation(path, handle, directory):
        current = path.stat(follow_symlinks=False)
        attributes = base._Attributes()
        if not base._kernel.GetFileInformationByHandleEx(
                handle, 9, ctypes.byref(attributes), ctypes.sizeof(attributes)):
            raise ctypes.WinError(ctypes.get_last_error())
        identity = base._identity(handle)
        if (current.st_file_attributes & 0x400 or attributes.attributes & 0x400 or
                not (stat.S_ISDIR(current.st_mode) if directory else stat.S_ISREG(current.st_mode)) or
                (not directory and current.st_nlink != 1) or
                identity != (current.st_dev, current.st_ino)):
            raise ValueError('file/ancestor identity, regular status, reparse or nlink drift')
        return dict(identity=identity, directory=directory,
                    reparse=False, nlink=current.st_nlink,
                    size_bytes=None if directory else current.st_size)

    def _open(self, path, directory):
        _RUNTIME()
        before = path.stat(follow_symlinks=False)
        if (before.st_file_attributes & 0x400 or (not directory and before.st_nlink != 1) or
                not (stat.S_ISDIR(before.st_mode) if directory else stat.S_ISREG(before.st_mode))):
            raise ValueError('regular local files and non-reparse ancestors required')
        handle = base._kernel.CreateFileW(str(path), 0x80 if directory else 0x80000000,
            3 if directory else 1, None, 3, 0x00200000 | (0x02000000 if directory else 0x80), None)
        if handle == base._INVALID:
            raise ctypes.WinError(ctypes.get_last_error())
        self._capsule[0](handle)
        self._handles.append(handle)
        observed = self._observation(path, handle, directory)
        if observed['identity'] != (before.st_dev, before.st_ino):
            raise ValueError('file identity changed during acquisition')
        self._entry[path] = (handle, observed)
        self._identities[path] = observed['identity']
        if not directory:
            self._files[path] = handle
        if path in self._science and observed['size_bytes'] != self._science[path][1]:
            raise ValueError('scientific input size differs')
        return handle

    def _check_hooks(self, *, scientific_read=False):
        _RUNTIME()
        super()._check_hooks()
        self._check_control()
        if (self._state != 'active' or self._expected is not self._bound_expected or
                self._paths is not self._bound_paths or self._science is not self._bound_science or
                self._guard is not self._owner_guard or self._capsule is not self._bound_capsule):
            raise ValueError('scientific input lease state or allowlist changed')
        _verify_functions(self._capsule_signatures)
        self._capsule[2]()
        if scientific_read: self.full_scientific_checks += 1
        else: self.full_checkpoint_checks += 1

    def _check_control(self):
        current = (self._capsule_signatures, self._release_recipe, self._state_recipe, self._verify_recipe,
                   self._function_type, self._cell_type, self._installed_reader,
                   self._owner_guard, self._path_type, self._restore_read, self._science_keys)
        if self._control is not self._bound_control or any(
                value is not expected for value, expected in zip(current, self._bound_control)):
            raise ValueError('ownership control binding changed')

    def _install_dispatch(self):
        owner, guard, cached = self, self._bound_control[7], self._data
        key_function, original = base._key, self._bound_control[9]
        light, full, control = base.CodeReadLease._check_hooks, type(self)._check_hooks, type(self)._check_control
        light_code, full_code, control_code = light.__code__, full.__code__, control.__code__
        science_keys = self._bound_control[10]
        def read(path):
            with guard:
                if (light.__code__ is not light_code or full.__code__ is not full_code or
                        control.__code__ is not control_code or base.CodeReadLease._check_hooks is not light or
                        type(owner)._check_hooks is not full or type(owner)._check_control is not control):
                    raise ValueError('read dispatch checker changed')
                light(owner)
                control(owner)
                key = key_function(path)
                raw = cached.get(key)
                if raw is not None:
                    if key in science_keys:
                        full(owner, scientific_read=True)
                    else:
                        owner.light_code_checks += 1
                    owner.hits += 1
                    owner._hits_by_path[key] = owner._hits_by_path.get(key, 0)+1
                    return raw
                owner.fallback_reads += 1
            return original(path)
        self._cached_read = read
        self._wrapper_code, self._wrapper_defaults, self._wrapper_keywords = read.__code__, read.__defaults__, read.__kwdefaults__
        self._wrapper_closure = tuple(c.cell_contents for c in read.__closure__ or ())
        new_control = (*self._bound_control[:6], read, *self._bound_control[7:])
        if self._bound_control[8].read_bytes is not self._installed_reader:
            raise ValueError('foreign read alias appeared during dispatch installation')
        self._bound_control[8].read_bytes = read
        self._installed_reader = read
        self._control = self._bound_control = new_control

    def __enter__(self):
        if self._state != 'new':
            raise ValueError('scientific input byte lease is single-use')
        try:
            _RUNTIME()
            self._check_control()
            _verify_functions(self._capsule_signatures)
            super().__enter__()
            self._installed_reader = self._cached_read
            self._control = self._bound_control = (*self._bound_control[:6], self._installed_reader,
                                                   *self._bound_control[7:])
            self._hook_installed = True
            self._install_dispatch()
            self._capsule[1]()
            self._capsule_signatures = _function_signatures(self._capsule)
            self._state_recipe = _recipe(self._capsule[4])
            self._control = self._bound_control = (self._capsule_signatures, self._release_recipe,
                self._state_recipe, *self._bound_control[3:])
            self._check_hooks()
            return self
        except BaseException as error:
            self._first_failure = repr(error)
            if self._hook_installed and self._bound_control[8].read_bytes is self._bound_control[6]:
                self._bound_control[8].read_bytes = self._bound_control[9]
            self._hook_restored = self._bound_control[8].read_bytes is self._bound_control[9]
            if self._state not in ('closed', 'cleanup_failed'):
                self._release()
            self._finish_receipt()
            raise

    def _release(self):
        failures = []
        try:
            _RUNTIME()
            self._check_control()
        except BaseException as error:
            failures.append(error)
        try:
            self._from_recipe(self._bound_control[3])(self._bound_control[0])
        except BaseException as error:
            failures.append(error)
        failures.extend(self._from_recipe(self._bound_control[1])())
        self._cleanup_errors.extend(failures)
        self._state = 'cleanup_failed' if self._owned_state()[1] else 'closed'
        return failures

    def _from_recipe(self, recipe):
        code, namespace, name, defaults, values, keywords = recipe
        cells = tuple(self._bound_control[5](value) for value in values)
        fn = self._bound_control[4](code, namespace, name, defaults, cells or None)
        fn.__kwdefaults__ = dict(keywords) or None
        return fn

    def _owned_state(self):
        return self._from_recipe(self._bound_control[2])()

    def _facts(self):
        pins = {str(p): pin for p, pin in self._bound_expected.items()}
        hits = dict(self._hits_by_path)
        return dict(schema='h1_static_scientific_input_read_lease_draft_v2',
                    status='DRAFT_NONAUTHORITATIVE', files_sha256=pins,
                    scientific_inputs={str(p): dict(sha256=pin, size_bytes=size)
                                       for p, (pin, size) in self._bound_science.items()},
                    code_file_count=len(self._code_paths), file_count=len(pins),
                    hits_by_path=hits, code_read_hits=sum(hits.get(key, 0) for key in self._code_keys),
                    scientific_input_read_hits=sum(hits.get(key, 0) for key in self._science_keys),
                    fallback_reads=self.fallback_reads, held_handles=len(self._owned_state()[1]),
                    static_scientific_input_bytes_cached=True,
                    repair_cap_table_bytes_cached=True,
                    raw_archive_or_source_rows_cached=False,
                    registry_objects_cached=False, numerical_result_cache=False,
                    saved_record_cache=False, solver_result_cache=False,
                    per_call_os_open=False,
                    cached_bytes_immutable_under_held_handles=True,
                    caller_hash_execution_proven_by_this_helper=False,
                    runtime_validation_schedule='light_on_code_hit; full_on_scientific_hit_and_lifecycle_checkpoint',
                    light_code_checks=self.light_code_checks,
                    full_scientific_checks=self.full_scientific_checks,
                    full_checkpoint_checks=self.full_checkpoint_checks,
                    fallback_dispatch_checks='original v1 hook checks and control identity; original fresh OS read',
                    distribution_discovery_cached=False,
                    this_code_lease_caches_package_versions=False,
                    production_seal=False, formal_result=False,
                    formal_execution_ready=False, native_execution_authorized=False,
                    resource_admission=False)

    def receipt(self):
        with self._bound_control[7]:
            self._check_hooks()
            return self._facts()

    def _finish_receipt(self):
        facts = self._facts()
        opened, pending, observations, _ = self._owned_state()
        expected_paths = {p for p, _, _ in observations}
        facts.update(state=self._state, all_handles_closed=not pending,
                     opened_handle_count=len(opened), closed_handle_count=len(opened)-len(pending),
                     hook_installed=self._hook_installed,
                     original_alias_restored=self._hook_restored,
                     foreign_alias_preserved=self._foreign_hook_preserved,
                     entry_observations={str(p): dict(row) for p, _, row in observations},
                     exit_observations={str(p): row for p, row in self._exit.items()},
                     exit_files_and_ancestors_verified=(set(self._exit) == expected_paths
                         and bool(expected_paths) and all(row.get('verified') for row in self._exit.values())),
                     first_failure=self._first_failure,
                     cleanup_errors=[repr(error) for error in self._cleanup_errors])
        self._receipt = facts
        self._data = MappingProxyType({})
        self._bound_data = None
        self._wrapper_closure = ()
        self._cached_read = None

    def closed_receipt(self):
        if self._receipt is None:
            raise ValueError('terminal byte lease required')
        # JSON-compatible detached copy; callers cannot mutate internal evidence.
        import json
        return json.loads(json.dumps(self._receipt))

    def retry_cleanup(self):
        with self._bound_control[7]:
            _RUNTIME()
            if self._state != 'cleanup_failed':
                raise ValueError('failed cleanup with retained handles required for retry')
            self._release()
            self._finish_receipt()
            return self.closed_receipt()

    def __exit__(self, kind, value, tb):
        errors = []
        with self._bound_control[7]:
            try:
                try:
                    self._check_hooks()
                except BaseException as error:
                    errors.append(error)
                # A changed verifier is never executed; the captured closer
                # still releases the exact owned handle set.
                try:
                    _RUNTIME()
                except BaseException as error:
                    if all(error is not prior for prior in errors): errors.append(error)
                else:
                    for path, handle, frozen in self._owned_state()[2]:
                        before = dict(frozen)
                        before_pin = before.pop('sha256', None)
                        try:
                            current = self._observation(path, handle, before['directory'])
                            if current != before:
                                raise ValueError('exit file/ancestor observation differs')
                            if not before['directory']:
                                raw = self._read(path)
                                held = base._bytes(handle, self._max_bytes)
                                if (raw != self._data[base._key(path)] or held != raw or
                                        sha256(raw).hexdigest() != self._bound_expected[path] or
                                        sha256(raw).hexdigest() != before_pin):
                                    raise ValueError('exit file bytes or SHA256 differs')
                                current['sha256'] = sha256(raw).hexdigest()
                            self._exit[path] = dict(current, verified=True)
                        except BaseException as error:
                            self._exit[path] = dict(verified=False, error=repr(error))
                            errors.append(error)
            finally:
                # Compare-and-swap protects a binding installed by someone else.
                if self._bound_control[8].read_bytes is self._bound_control[6]:
                    self._bound_control[8].read_bytes = self._bound_control[9]
                    self._hook_restored = True
                else:
                    self._foreign_hook_preserved = True
                    errors.append(ValueError('foreign read alias preserved during cleanup'))
                errors.extend(self._release())
                if value is not None:
                    self._first_failure = repr(value)
                elif errors:
                    self._first_failure = repr(errors[0])
                self._cleanup_errors.extend(error for error in errors
                                            if all(error is not prior for prior in self._cleanup_errors))
                self._finish_receipt()
        if value is None and errors:
            raise errors[0]
        return False



def _install_runtime():
    namespace = globals()
    own_module = sys.modules[__name__]
    base_module = base
    sys_module, registry_identity = sys, id(sys.modules)
    functions = []
    bindings = [(base, name, value) for name, value in vars(base).items()
                if not name.startswith('__')]
    class_bindings = []
    for obj, names in ((base, ('CodeReadLease', '_key', '_bytes', '_identity', '_Attributes', '_kernel', '_INVALID')),
                       (base._kernel, ('CreateFileW', 'CloseHandle', 'GetFileInformationByHandleEx',
                                       'GetFileSizeEx', 'SetFilePointerEx', 'ReadFile')),
                       (stat, ('S_ISDIR', 'S_ISREG')),
                       (Path, ('stat', 'open', 'is_absolute', 'is_relative_to')),
                       (base.os.path, ('normcase',))):
        bindings.extend((obj, name, getattr(obj, name)) for name in names)
    for cls in (base.CodeReadLease, StaticScientificInputReadLease):
        for name, descriptor in vars(cls).items():
            fn = descriptor.__func__ if isinstance(descriptor, staticmethod) else descriptor
            if isinstance(fn, FunctionType):
                class_bindings.append((cls, name, descriptor))
                functions.append(fn)
    functions.extend((base._key, base._bytes, base._identity, scientific_inputs, _inventory, _install_runtime,
                      _recipe, _function_signatures, _verify_functions, _safe_closer,
                      Path.stat, Path.open, Path.is_absolute, Path.is_relative_to, Path.read_bytes, base.os.path.normcase))
    states = tuple((fn, fn.__code__, fn.__defaults__, fn.__kwdefaults__) for fn in functions)
    closures = tuple((fn, tuple(id(c.cell_contents) for c in fn.__closure__))
                     for fn in functions if fn.__closure__)
    values = tuple((fn, repr(fn.__defaults__), repr(fn.__kwdefaults__)) for fn in functions
                   if fn.__defaults__ is not None or fn.__kwdefaults__ is not None)
    kernel_signatures = tuple((getattr(base._kernel,name), tuple(getattr(base._kernel,name).argtypes or ()),
                               getattr(base._kernel,name).restype,getattr(getattr(base._kernel,name),'errcheck',None))
                              for name in ('CreateFileW','CloseHandle','GetFileInformationByHandleEx',
                                           'GetFileSizeEx','SetFilePointerEx','ReadFile')
                              if isinstance(getattr(base._kernel,name),ctypes._CFuncPtr))
    globals_fixed = tuple((name, namespace[name]) for name in (
        'base', 'ctypes', 'sha256', 'Path', 'stat', 'sys', 'FunctionType', 'CellType', 'MappingProxyType',
        'SCIENTIFIC_INPUTS', 'scientific_inputs', '_inventory', '_recipe', '_function_signatures',
        '_verify_functions', '_safe_closer', 'StaticScientificInputReadLease', '_install_runtime'))
    module_fixed = tuple((obj, name, getattr(obj, name, None))
                         for obj in (own_module, base_module)
                         for name in ('__file__', '__name__', '__spec__', '__loader__', '__package__'))
    def check():
        if (namespace.get('_RUNTIME') is not check or
                id(sys_module.modules) != registry_identity or
                sys_module.modules.get(own_module.__name__) is not own_module or
                sys_module.modules.get(base_module.__name__) is not base_module or
                any(namespace.get(name) is not value for name, value in globals_fixed) or
                any(getattr(obj, name, None) is not value for obj, name, value in bindings) or
                any(vars(obj).get(name) is not value for obj, name, value in class_bindings) or
                any(getattr(obj, name, None) is not value for obj, name, value in module_fixed) or
                any(fn.__code__ is not code or fn.__defaults__ is not defaults or
                    fn.__kwdefaults__ is not keywords for fn, code, defaults, keywords in states) or
                any(tuple(id(c.cell_contents) for c in fn.__closure__) != closure for fn, closure in closures) or
                any(repr(fn.__defaults__) != defaults or repr(fn.__kwdefaults__) != keywords
                    for fn, defaults, keywords in values) or
                any(tuple(fn.argtypes or ()) != args or fn.restype is not result or
                    getattr(fn,'errcheck',None) is not errcheck
                    for fn,args,result,errcheck in kernel_signatures)):
            raise ValueError('scientific input byte lease runtime dependency changed')
    return check


_RUNTIME = _install_runtime()
