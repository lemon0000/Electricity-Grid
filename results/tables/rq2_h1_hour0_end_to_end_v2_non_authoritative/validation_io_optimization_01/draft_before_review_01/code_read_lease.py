"""Non-authoritative Windows code-read optimization; input files stay uncached.

Cached bytes are protected by live OS handles denying both writes and deletion.
Every parent directory is held against rename. This context is process-local and
does not cache numerical results, sources, configurations, or saved records.
"""
import ctypes
from ctypes import wintypes
from hashlib import sha256
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
_kernel.GetFileSizeEx.argtypes=(wintypes.HANDLE,ctypes.POINTER(ctypes.c_longlong))
_kernel.GetFileSizeEx.restype=wintypes.BOOL
_kernel.SetFilePointerEx.argtypes=(wintypes.HANDLE,ctypes.c_longlong,wintypes.LPVOID,wintypes.DWORD)
_kernel.SetFilePointerEx.restype=wintypes.BOOL
_kernel.ReadFile.argtypes=(wintypes.HANDLE,wintypes.LPVOID,wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),wintypes.LPVOID)
_kernel.ReadFile.restype=wintypes.BOOL
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


def _bytes(handle,cap):
    length=ctypes.c_longlong()
    if not _kernel.GetFileSizeEx(handle,ctypes.byref(length)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not 0<=length.value<=cap:raise ValueError('code file byte bound exceeded')
    if not _kernel.SetFilePointerEx(handle,0,None,0):raise ctypes.WinError(ctypes.get_last_error())
    blocks=[];remaining=length.value
    while remaining:
        buffer=ctypes.create_string_buffer(min(remaining,1024**2));count=wintypes.DWORD()
        if not _kernel.ReadFile(handle,buffer,len(buffer),ctypes.byref(count),None):
            raise ctypes.WinError(ctypes.get_last_error())
        if count.value==0:raise ValueError('short code read from held handle')
        blocks.append(buffer.raw[:count.value]);remaining-=count.value
    return b''.join(blocks)


class CodeReadLease:
    """One explicit, bounded, immutable code/metadata allowlist per context."""
    def __init__(self,expected,*,root,max_files=4096,max_bytes=64*1024**2):
        self._root=Path(root)
        self._expected={Path(p):pin for p,pin in expected.items()}
        self._paths=tuple(sorted(self._expected,key=str))
        if (not self._paths or len(self._paths)>max_files
                or _key(self._root) is None
                or any(_key(p) is None or p.suffix!='.py' or not p.is_relative_to(self._root)
                       or type(self._expected[p]) is not str or len(self._expected[p])!=64
                       or any(c not in '0123456789abcdef' for c in self._expected[p]) for p in self._paths)):
            raise ValueError('bounded exact repo code allowlist and SHA256 pins required')
        self._max_bytes=max_bytes
        self._handles=[];self._identities={};self._data=MappingProxyType({})
        self._files={};self._guard=RLock();self._state='new'
        self._read=Path.read_bytes
        self.hits=0;self.fallback_reads=0

    def _open(self,path,directory):
        before=path.stat(follow_symlinks=False)
        if (before.st_file_attributes&0x400 or (not directory and before.st_nlink!=1) or
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
        if not directory:self._files[path]=handle
        return handle

    def _check_hooks(self):
        fn=self._cached_read
        if (Path.read_bytes is not fn or fn.__code__ is not self._wrapper_code
                or fn.__defaults__!=self._wrapper_defaults or fn.__kwdefaults__!=self._wrapper_keywords
                or tuple(c.cell_contents for c in fn.__closure__ or ())!=self._wrapper_closure):
            raise ValueError('code lease read dispatch changed')

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
                    handle=self._open(path,False)
                    raw=_bytes(handle,self._max_bytes-total);total+=len(raw)
                    if total>self._max_bytes:raise ValueError('code lease byte bound exceeded')
                    if sha256(raw).hexdigest()!=self._expected[path]:raise ValueError('expected code bytes differ')
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
                self._cached_read=read
                self._wrapper_code=read.__code__;self._wrapper_defaults=read.__defaults__
                self._wrapper_keywords=read.__kwdefaults__
                self._wrapper_closure=tuple(c.cell_contents for c in read.__closure__ or ())
                if Path.read_bytes is not self._read:
                    raise ValueError('read dispatch changed during lease acquisition')
                Path.read_bytes=read
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
                file_count=len(self._paths),code_read_hits=self.hits,
                fallback_reads=self.fallback_reads,held_handles=len(self._handles),
                source_or_result_cache=False,numerical_result_cache=False,
                distribution_discovery_cached=False,package_versions_cached=False,formal_result=False)

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
                    if ((current.st_dev,current.st_ino)!=self._identities[path]
                            or self._read(path)!=self._data[_key(path)]
                            or _bytes(self._files[path],self._max_bytes)!=self._data[_key(path)]):
                        raise ValueError('code lease bytes or pathname identity changed')
            finally:
                if Path.read_bytes is self._cached_read:Path.read_bytes=self._read
                self._release()
