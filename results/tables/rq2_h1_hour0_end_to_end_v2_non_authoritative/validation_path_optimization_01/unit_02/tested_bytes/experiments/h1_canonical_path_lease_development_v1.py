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


SCHEMA = 'h1_canonical_path_lease_development_v1'


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
    return os.path.normcase(str(path))


def _eligible(path):
    # Resolve aliases and lexical normalization through the predecessor instead.
    return (type(path) is type(Path()) and path.is_absolute()
        and len(path.anchor) == 3 and path.anchor[1:] == ':\\'
        and all(part not in ('.', '..') and '~' not in part
                and ':' not in part and not part.endswith((' ', '.'))
                for part in path.parts[1:]))


class CanonicalPathLease:
    """One thread, explicit roots and bounded handles; no file-content cache.

    Directory handles deny WRITE and DELETE sharing. This prevents replacement,
    rename and conversion to a reparse point while child files remain writable.
    Unsupported paths and resource saturation retain predecessor behavior.
    """
    def __init__(self, module, roots, *, max_directories=4096, max_paths=16384):
        if os.name != 'nt':
            raise ValueError('Windows directory handles required')
        self._module = module
        self._original = module._path
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
                or self._wrapper.__code__ is not self._wrapper_code):
            raise ValueError('canonical path lease lifetime or dispatch changed')

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
        try:
            identity = _FileId()
            attributes = _Attributes()
            for kind, value in ((18, identity), (9, attributes)):
                if not self._kernel.GetFileInformationByHandleEx(
                        handle, kind, ctypes.byref(value), ctypes.sizeof(value)):
                    raise ctypes.WinError(ctypes.get_last_error())
            actual = identity.volume, int.from_bytes(identity.file_id, 'little')
            after = path.stat(follow_symlinks=False)
            if (attributes.attributes & 0x400 or after.st_file_attributes & 0x400
                    or actual != (before.st_dev, before.st_ino)
                    or actual != (after.st_dev, after.st_ino)):
                raise ValueError('directory changed during handle acquisition')
            self._directories[key] = path, handle, actual
            self.acquisitions += 1
        except BaseException:
            self._kernel.CloseHandle(handle)
            raise

    def _hold_parents(self, path):
        parents = tuple(reversed(path.parents))
        pending = [p for p in parents if _key(p) not in self._directories]
        if len(pending) + len(self._directories) > self._max_directories:
            return False
        for directory in pending:
            self._open_directory(directory)
        return True

    def _path(self, value):
        self._check()
        path = Path(value)
        if not _eligible(path) or not any(path.is_relative_to(root) for root in self._roots):
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
            self.hits += 1
            return path
        self.fallbacks += 1
        checked = self._original(value)
        if len(self._paths) >= self._max_paths or checked != path:
            return checked
        try:
            if not self._hold_parents(path):
                return checked
        except OSError:
            # A writer or unsupported volume prevents this optional optimization.
            # The completed predecessor check remains the result of this call.
            return checked
        # Close the acquisition window before admitting a reusable path.
        if self._original(value) != checked:
            raise ValueError('canonical path changed during directory acquisition')
        self._paths[key] = path
        return checked

    def __enter__(self):
        if self._state != 'new' or self._module._path is not self._original:
            raise ValueError('canonical path lease is single-use')
        if self._owner != (os.getpid(), threading.get_ident()):
            raise ValueError('same-process same-thread path lease required')
        owner = self
        def path(value):
            return owner._path(value)
        self._wrapper = path
        self._wrapper_code = path.__code__
        self._module._path = path
        self._state = 'active'
        return self

    def receipt(self):
        self._check()
        return dict(schema=SCHEMA, hits=self.hits, fallback_calls=self.fallbacks,
            directory_handles=len(self._directories), canonical_paths=len(self._paths),
            ancestor_write_delete_sharing=False, leaf_lstat_fresh=True,
            file_bytes_cached=False, numerical_results_cached=False,
            formal_result=False, formal_execution_ready=False)

    def __exit__(self, kind, error, tb):
        mismatch = None
        try:
            self._check()
        except BaseException as exc:
            mismatch = exc
        finally:
            self._module._path = self._original
            for path, handle, identity in reversed(tuple(self._directories.values())):
                self._kernel.CloseHandle(handle)
            self._directories.clear()
            self._paths.clear()
            self._state = 'closed'
        if mismatch is not None:
            raise mismatch

