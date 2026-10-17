"""Windows ancestor-handle optimization for bounded synthetic validation.

Only canonical directory traversal is reused. File bytes, file stamps, numerical
replay and every original validation boundary remain fresh. This development
context is not a production execution lease or a verification credential.
"""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import stat
import threading

from src.rq2_joint_deliverability_boundary_v1 import episode_store as _STORE


SCHEMA = 'h1_canonical_path_lease_development_v1'
_ORIGINAL = _STORE._path
_ORIGINAL_CODE = _ORIGINAL.__code__
_ORIGINAL_DEFAULTS = _ORIGINAL.__defaults__
_ORIGINAL_KEYWORDS = _ORIGINAL.__kwdefaults__


class HandleCleanupError(RuntimeError):
    pass


def _scope_registry():
    active = {}
    def register(owner, cleanup, handles):
        if id(owner) in active:
            raise ValueError('path cleanup already registered')
        active[id(owner)] = owner, cleanup, handles
    def release(owner):
        record = active.get(id(owner))
        if record is None or record[0] is not owner:
            raise ValueError('original registered path cleanup required')
        try:
            record[1]()
        finally:
            if not record[2]:
                del active[id(owner)]
    return register, release


_REGISTER, _RELEASE = _scope_registry()
del _scope_registry


class _FileId(ctypes.Structure):
    _fields_ = [('volume', ctypes.c_ulonglong), ('file_id', ctypes.c_ubyte * 16)]


class _Attributes(ctypes.Structure):
    _fields_ = [('attributes', wintypes.DWORD), ('tag', wintypes.DWORD)]


def _kernel_api():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.GetFileInformationByHandleEx.argtypes = (wintypes.HANDLE, ctypes.c_int,
        wintypes.LPVOID, wintypes.DWORD)
    kernel.GetFileInformationByHandleEx.restype = wintypes.BOOL
    return kernel


def _key(path):
    # Exact spelling also works on NTFS directories with case sensitivity enabled.
    # WindowsPath equality/normcase must not merge two different ancestors there.
    return str(path)


def _eligible(path):
    # Resolve aliases and lexical normalization through the predecessor instead.
    return (type(path) is type(Path()) and path.is_absolute()
        and len(path.anchor) == 3 and path.anchor[1:] == ':\\'
        and all(part not in ('.', '..') and '~' not in part
                and ':' not in part and not part.endswith((' ', '.'))
                for part in path.parts[1:]))


def _covered(path, root):
    return path.parts[:len(root.parts)] == root.parts


class CanonicalPathLease:
    """One thread, explicit roots and bounded handles; no file-content cache.

    Directory handles deny data-WRITE and DELETE sharing. Attribute-only writes
    can still alter reparse/case flags, so those are observed on every call.
    Unsupported paths and resource saturation retain predecessor behavior.
    """
    def __init__(self, module, roots, *, max_directories=4096, max_paths=16384):
        if os.name != 'nt':
            raise ValueError('Windows directory handles required')
        self._module = module
        self._original = module._path
        if (module is not _STORE or self._original is not _ORIGINAL
                or _ORIGINAL.__code__ is not _ORIGINAL_CODE
                or _ORIGINAL.__defaults__ != _ORIGINAL_DEFAULTS
                or _ORIGINAL.__kwdefaults__ != _ORIGINAL_KEYWORDS):
            raise ValueError('exact unchanged episode_store path function required')
        self._roots = tuple(Path(p) for p in roots)
        if (not self._roots or any(not _eligible(p) for p in self._roots)
                or type(max_directories) is not int or not 1 <= max_directories <= 4096
                or type(max_paths) is not int or not 1 <= max_paths <= 16384):
            raise ValueError('explicit canonical roots and bounded capacities required')
        self._max_directories = max_directories
        self._max_paths = max_paths
        self._kernel = _kernel_api()
        self._directories = {}
        self._paths = {}
        self._state = 'new'
        self._owner = os.getpid(), threading.get_ident()
        self.hits = self.fallbacks = self.acquisitions = 0

    def _check(self):
        if (self._state != 'active'
                or self._owner != (os.getpid(), threading.get_ident())
                or self._module._path is not self._wrapper
                or self._wrapper.__code__ is not self._wrapper_code
                or self._wrapper.__defaults__ is not None
                or self._wrapper.__kwdefaults__ is not None
                or tuple(c.cell_contents for c in self._wrapper.__closure__ or ()) != self._wrapper_closure):
            raise ValueError('canonical path lease lifetime or dispatch changed')
        self._fixed()

    def _open_directory(self, path):
        key = _key(path)
        if key in self._directories:
            return
        before = path.stat(follow_symlinks=False)
        if not stat.S_ISDIR(before.st_mode) or before.st_file_attributes & 0x400:
            raise ValueError('canonical non-reparse directory required')
        # FILE_LIST_DIRECTORY | FILE_READ_ATTRIBUTES, FILE_SHARE_READ, OPEN_EXISTING.
        # Attribute-only opens do not participate in Windows share-access checks.
        # FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS.
        handle = self._kernel.CreateFileW(str(path), 0x81, 1, None, 3, 0x02200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        self._directories[key] = path, handle, None, None
        try:
            identity = _FileId()
            attributes = _Attributes()
            sensitive = wintypes.DWORD()
            for kind, value in ((18, identity), (9, attributes), (23, sensitive)):
                if not self._kernel.GetFileInformationByHandleEx(
                        handle, kind, ctypes.byref(value), ctypes.sizeof(value)):
                    raise ctypes.WinError(ctypes.get_last_error())
            actual = identity.volume, int.from_bytes(identity.file_id, 'little')
            after = path.stat(follow_symlinks=False)
            if (attributes.attributes & 0x400 or after.st_file_attributes & 0x400
                    or actual != (before.st_dev, before.st_ino)
                    or actual != (after.st_dev, after.st_ino)):
                raise ValueError('directory changed during handle acquisition')
            self._directories[key] = path, handle, actual, sensitive.value
            self.acquisitions += 1
        except BaseException:
            self._rollback([key])
            raise

    def _hold_parents(self, path):
        parents = tuple(reversed(path.parents))
        pending = [p for p in parents if _key(p) not in self._directories]
        if len(pending) + len(self._directories) > self._max_directories:
            return None
        added = []
        try:
            for directory in pending:
                self._open_directory(directory)
                added.append(_key(directory))
        except BaseException:
            self._rollback(added)
            raise
        return added

    def _rollback(self, keys):
        failed = []
        for key in reversed(keys):
            path, handle, identity, sensitive = self._directories[key]
            try:
                if self._kernel.CloseHandle(handle):
                    del self._directories[key]
                else:
                    failed.append((str(path), ctypes.get_last_error()))
            except BaseException as error:
                failed.append((str(path), repr(error)))
        if failed:
            raise HandleCleanupError('directory handle cleanup failed: ' + repr(failed))

    def _observe_parents(self, entries):
        attributes = _Attributes()
        sensitive = wintypes.DWORD()
        for path, handle, identity, expected_sensitive in entries:
            if not self._kernel.GetFileInformationByHandleEx(
                    handle, 9, ctypes.byref(attributes), ctypes.sizeof(attributes)):
                raise ctypes.WinError(ctypes.get_last_error())
            if attributes.attributes & 0x400:
                raise ValueError('reparse ancestor changed during path lease')
            if not self._kernel.GetFileInformationByHandleEx(
                    handle, 23, ctypes.byref(sensitive), ctypes.sizeof(sensitive)):
                raise ctypes.WinError(ctypes.get_last_error())
            if sensitive.value != expected_sensitive:
                raise ValueError('ancestor case sensitivity changed during path lease')

    def _path(self, value):
        self._check()
        path = Path(value)
        if not _eligible(path) or not any(_covered(path, root) for root in self._roots):
            self.fallbacks += 1
            return self._original(value)
        key = _key(path)
        retained = self._paths.get(key)
        if retained is not None:
            # The final component remains mutable and must be observed afresh.
            try:
                info = path.lstat()
            except FileNotFoundError:
                pass
            else:
                if info.st_file_attributes & 0x400:
                    raise ValueError('reparse paths are not supported by the local store')
            self._observe_parents(retained[1])
            self.hits += 1
            return path
        self.fallbacks += 1
        checked = self._original(value)
        if len(self._paths) >= self._max_paths or checked != path:
            return checked
        added = None
        try:
            added = self._hold_parents(path)
            if added is None:
                return checked
        except OSError:
            # A writer or unsupported volume prevents this optional optimization.
            # The completed predecessor check remains the result of this call.
            return checked
        try:
            # Close the acquisition window before admitting a reusable path.
            if self._original(value) != checked:
                raise ValueError('canonical path changed during directory acquisition')
            self._check()
            self._paths[key] = path, tuple(self._directories[_key(p)] for p in reversed(path.parents))
        except BaseException:
            self._rollback(added)
            raise
        return checked

    def __enter__(self):
        if (type(self) is not CanonicalPathLease or self._state != 'new'
                or self._module._path is not self._original):
            raise ValueError('canonical path lease is single-use')
        if self._owner != (os.getpid(), threading.get_ident()):
            raise ValueError('same-process same-thread path lease required')
        owner = self
        dispatch, check = type(self)._path, type(self)._check
        module, original, roots = self._module, self._original, self._roots
        directories, paths, kernel = self._directories, self._paths, self._kernel
        restore_dispatch = module, original
        helpers = (_key, _eligible, _covered, _kernel_api, _FileId, _Attributes, _STORE, _ORIGINAL, _REGISTER, _RELEASE)
        methods = tuple((name, getattr(CanonicalPathLease, name)) for name in (
            '_check', '_open_directory', '_hold_parents', '_rollback', '_observe_parents', '_path',
            '__enter__', 'receipt', '__exit__'))
        functions = (original, *helpers[:4], _REGISTER, _RELEASE, *(fn for name, fn in methods))
        codes = tuple((fn, fn.__code__, repr(fn.__defaults__), repr(fn.__kwdefaults__)) for fn in functions)
        def fixed():
            if (self._module is not module or module is not _STORE
                    or original is not _ORIGINAL or self._original is not original
                    or self._roots is not roots or self._directories is not directories
                    or self._paths is not paths or self._kernel is not kernel
                    or getattr(self, '_restore_dispatch', None) is not restore_dispatch
                    or '_path' in vars(self) or '_check' in vars(self)
                    or helpers != (_key, _eligible, _covered, _kernel_api, _FileId, _Attributes, _STORE, _ORIGINAL, _REGISTER, _RELEASE)
                    or any(getattr(CanonicalPathLease, name) is not fn for name, fn in methods)
                    or any(fn.__code__ is not code or repr(fn.__defaults__) != defaults
                           or repr(fn.__kwdefaults__) != keywords for fn, code, defaults, keywords in codes)):
                raise ValueError('canonical path lease binding changed')
        def path(value):
            fixed()
            check(owner)
            return dispatch(owner, value)
        self._fixed = fixed
        self._restore_dispatch = restore_dispatch
        self._wrapper = path
        self._wrapper_code = path.__code__
        self._wrapper_closure = tuple(c.cell_contents for c in path.__closure__ or ())
        self._module._path = path
        self._state = 'active'
        close_handle = kernel.CloseHandle
        def cleanup():
            module._path = original
            failures = []
            for key in reversed(tuple(directories)):
                name, handle, identity, sensitive = directories[key]
                try:
                    if close_handle(handle):
                        del directories[key]
                    else:
                        failures.append((str(name), ctypes.get_last_error()))
                except BaseException as exc:
                    failures.append((str(name), repr(exc)))
            paths.clear()
            self._state = 'cleanup_failed' if directories else 'closed'
            if failures:
                raise HandleCleanupError('directory handle cleanup failed: ' + repr(failures))
        _REGISTER(self, cleanup, directories)
        return self

    def receipt(self):
        self._check()
        return dict(schema=SCHEMA, hits=self.hits, fallback_calls=self.fallbacks,
            directory_handles=len(self._directories), canonical_paths=len(self._paths),
            ancestor_write_delete_sharing=False, leaf_lstat_fresh=True,
            ancestor_reparse_and_case_flags_fresh=True,
            file_bytes_cached=False, numerical_results_cached=False,
            formal_result=False, formal_execution_ready=False)

    def __exit__(self, kind, error, tb):
        mismatch = None
        cleanup_error = None
        try:
            self._check()
        except BaseException as exc:
            mismatch = exc
        finally:
            try:
                _RELEASE(self)
            except BaseException as exc:
                cleanup_error = exc
        if cleanup_error is not None:
            errors = [exc for exc in (error, mismatch, cleanup_error) if exc is not None]
            raise BaseExceptionGroup('path operation and handle cleanup errors', errors)
        if mismatch is not None:
            raise mismatch from error

