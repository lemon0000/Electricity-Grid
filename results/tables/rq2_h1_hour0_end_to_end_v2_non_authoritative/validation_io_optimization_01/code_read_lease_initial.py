"""Non-authoritative Windows code-read optimization; input files stay uncached.

Cached bytes are protected by live OS handles denying both writes and deletion.
Every parent directory is held against rename. This context is process-local and
does not cache numerical results, sources, configurations, or saved records.
"""
import ctypes
from ctypes import wintypes
from hashlib import sha256
import importlib.metadata as metadata
import os
from pathlib import Path
import stat
from threading import RLock
from types import MappingProxyType


class _FileId(ctypes.Structure):
    _fields_=[('volume',ctypes.c_ulonglong),('file_id',ctypes.c_ubyte*16)]


_kernel=ctypes.WinDLL('kernel32',use_last_error=True)
_kernel.CreateFileW.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,
    wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE)
_kernel.CreateFileW.restype=wintypes.HANDLE
_kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
_kernel.CloseHandle.restype=wintypes.BOOL
_kernel.GetFileInformationByHandleEx.argtypes=(wintypes.HANDLE,ctypes.c_int,
    wintypes.LPVOID,wintypes.DWORD)
_kernel.GetFileInformationByHandleEx.restype=wintypes.BOOL
_INVALID=ctypes.c_void_p(-1).value


def _identity(handle):
    info=_FileId()
    if not _kernel.GetFileInformationByHandleEx(handle,18,ctypes.byref(info),ctypes.sizeof(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    return info.volume,int.from_bytes(info.file_id,'little')


def _key(path):
    path=Path(path)
    # Collapsing '..' across a reparse point can name a different physical file.
    if not path.is_absolute() or '..' in path.parts:return None
    return os.path.normcase(str(path))


def loaded_code_paths():
    import sys
    result=set()
    for module in tuple(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename and Path(filename).suffix=='.py':result.add(Path(filename).resolve())
    return result


def distribution_metadata_paths(names):
    result=set()
    for name in names:
        distribution=metadata.distribution(name)
        path=getattr(distribution,'_path',None)
        if isinstance(path,Path):
            candidate=path/'METADATA'
            if candidate.is_file():result.add(candidate.resolve())
    return result


class CodeReadLease:
    """One explicit, bounded, immutable code/metadata allowlist per context."""
    def __init__(self,paths,*,max_files=4096,max_bytes=64*1024**2,cache_versions=True):
        self._paths=tuple(sorted({Path(p).absolute() for p in paths},key=str))
        if (not self._paths or len(self._paths)>max_files
                or any(p.suffix!='.py' and p.name!='METADATA' for p in self._paths)):
            raise ValueError('bounded code and distribution METADATA allowlist required')
        self._max_bytes=max_bytes;self._cache_versions=cache_versions
        self._handles=[];self._identities={};self._data=MappingProxyType({})
        self._guard=RLock();self._state='new';self._versions={}
        self._read=Path.read_bytes;self._version=metadata.Distribution.version
        self.hits=0;self.version_hits=0;self.fallback_reads=0

    def _open(self,path,directory):
        before=path.stat(follow_symlinks=False)
        if (before.st_file_attributes&0x400 or
                not (stat.S_ISDIR(before.st_mode) if directory else stat.S_ISREG(before.st_mode))):
            raise ValueError('regular local files and non-reparse ancestors required')
        # READ_ATTRIBUTES for directories; GENERIC_READ for immutable code bytes.
        handle=_kernel.CreateFileW(str(path),0x80 if directory else 0x80000000,
            3 if directory else 1,None,3,0x02000000 if directory else 0x80,None)
        if handle==_INVALID:raise ctypes.WinError(ctypes.get_last_error())
        self._handles.append(handle)
        identity=_identity(handle)
        after=path.stat(follow_symlinks=False)
        if identity!=(before.st_dev,before.st_ino) or identity!=(after.st_dev,after.st_ino):
            raise ValueError('code lease path changed during acquisition')
        self._identities[path]=identity

    def _check_hooks(self):
        if Path.read_bytes is not self._cached_read or metadata.Distribution.version is not self._cached_version:
            raise ValueError('code lease read or version dispatch changed')

    def __enter__(self):
        with self._guard:
            if self._state!='new':raise ValueError('code read lease is single-use')
            self._state='acquiring'
            try:
                # Top-down acquisition pins each pathname before opening children.
                directories={p for file in self._paths for p in file.parents}
                for path in sorted(directories,key=lambda p:(len(p.parts),str(p))):self._open(path,True)
                data={};total=0
                for path in self._paths:
                    self._open(path,False)
                    raw=self._read(path);total+=len(raw)
                    if total>self._max_bytes:raise ValueError('code lease byte bound exceeded')
                    data[_key(path)]=raw
                self._data=MappingProxyType(data)
                owner=self
                def read(path):
                    with owner._guard:
                        owner._check_hooks()
                        raw=owner._data.get(_key(path))
                        if raw is not None:
                            owner.hits+=1;return raw
                        owner.fallback_reads+=1
                        return owner._read(path)
                def version(distribution):
                    with owner._guard:
                        owner._check_hooks()
                        path=getattr(distribution,'_path',None)
                        key=_key(path/'METADATA') if type(distribution) is metadata.PathDistribution and isinstance(path,Path) else None
                        if owner._cache_versions and key in owner._data:
                            if key not in owner._versions:owner._versions[key]=owner._version.fget(distribution)
                            owner.version_hits+=1;return owner._versions[key]
                        return owner._version.fget(distribution)
                self._cached_read=read
                self._cached_version=property(version) if self._cache_versions else self._version
                if Path.read_bytes is not self._read or metadata.Distribution.version is not self._version:
                    raise ValueError('read dispatch changed during lease acquisition')
                Path.read_bytes=read;metadata.Distribution.version=self._cached_version
                self._state='active'
                return self
            except BaseException:
                self._release();raise

    def receipt(self):
        with self._guard:
            if self._state!='active':raise ValueError('live code lease required')
            self._check_hooks()
            return dict(schema='synthetic_code_read_lease_v1',
                files_sha256={str(p):sha256(self._data[_key(p)]).hexdigest() for p in self._paths},
                file_count=len(self._paths),code_read_hits=self.hits,version_hits=self.version_hits,
                fallback_reads=self.fallback_reads,held_handles=len(self._handles),
                source_or_result_cache=False,numerical_result_cache=False,
                distribution_discovery_cached=False,formal_result=False)

    def _release(self):
        errors=[]
        for handle in reversed(self._handles):
            if not _kernel.CloseHandle(handle):errors.append(ctypes.get_last_error())
        self._handles.clear();self._state='closed'
        if errors:raise OSError('code lease handle release failed: '+repr(errors))

    def __exit__(self,kind,value,tb):
        with self._guard:
            try:
                self._check_hooks()
                for path in self._paths:
                    current=path.stat(follow_symlinks=False)
                    if (current.st_dev,current.st_ino)!=self._identities[path] or self._read(path)!=self._data[_key(path)]:
                        raise ValueError('code lease bytes or pathname identity changed')
            finally:
                if Path.read_bytes is self._cached_read:Path.read_bytes=self._read
                if metadata.Distribution.version is self._cached_version:metadata.Distribution.version=self._version
                self._release()
