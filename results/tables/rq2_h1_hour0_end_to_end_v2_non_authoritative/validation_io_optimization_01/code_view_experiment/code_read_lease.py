"""Non-authoritative Windows code-read optimization; input files stay uncached.

Cached bytes are protected by live OS handles denying both writes and deletion.
Every parent directory is held against rename. This context is process-local and
does not cache numerical results, sources, configurations, or saved records.
"""
import ctypes
from ctypes import wintypes
from hashlib import sha256
import io
import msvcrt
import os
from pathlib import Path
import stat
import sys
from threading import RLock
from types import MappingProxyType


class _FileId(ctypes.Structure):
    _fields_=[('volume',ctypes.c_ulonglong),('file_id',ctypes.c_ubyte*16)]


class _Attributes(ctypes.Structure):
    _fields_=[('attributes',wintypes.DWORD),('tag',wintypes.DWORD)]


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
_kernel.GetCurrentProcess.restype=wintypes.HANDLE
_kernel.DuplicateHandle.argtypes=(wintypes.HANDLE,wintypes.HANDLE,wintypes.HANDLE,
    ctypes.POINTER(wintypes.HANDLE),wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
_kernel.DuplicateHandle.restype=wintypes.BOOL
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


class _CodeBytes(io.BytesIO):
    """Only the audited stable reader uses this view; fd is for its fstat calls."""
    def __init__(self,raw,fd,release):
        super().__init__(raw);self._fd=fd;self._release=release
    def fileno(self):
        if self.closed:raise ValueError('closed code view')
        return self._fd
    def writable(self):return False
    def write(self,*args):raise io.UnsupportedOperation('read-only code lease view')
    def truncate(self,*args):raise io.UnsupportedOperation('read-only code lease view')
    def getbuffer(self):return super().getbuffer().toreadonly()
    def close(self):
        if not self.closed:
            super().close();self._release()


class CodeReadLease:
    """One explicit, bounded, immutable code/metadata allowlist per context."""
    def __init__(self,expected,*,root,max_files=4096,max_bytes=64*1024**2,code_views=False):
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
        self._restore_read=self._read
        self._restore_open=Path.open;self._code_views=code_views
        self._view_type=_CodeBytes
        self._view_methods=tuple((name,getattr(_CodeBytes,name)) for name in
            ('__init__','fileno','writable','write','truncate','getbuffer','close','read','readinto','seek'))
        self._readers={};self._fds={};self._open_views=0;self.code_view_hits=0
        self.hits=0;self.fallback_reads=0;self._hits_by_path={}

    def _open(self,path,directory):
        before=path.stat(follow_symlinks=False)
        if (before.st_file_attributes&0x400 or (not directory and before.st_nlink!=1) or
                not (stat.S_ISDIR(before.st_mode) if directory else stat.S_ISREG(before.st_mode))):
            raise ValueError('regular local files and non-reparse ancestors required')
        # READ_ATTRIBUTES for directories; GENERIC_READ for immutable code bytes.
        handle=_kernel.CreateFileW(str(path),0x80 if directory else 0x80000000,
            3 if directory else 1,None,3,0x00200000|(0x02000000 if directory else 0x80),None)
        if handle==_INVALID:raise ctypes.WinError(ctypes.get_last_error())
        self._handles.append(handle)
        attributes=_Attributes()
        if not _kernel.GetFileInformationByHandleEx(handle,9,ctypes.byref(attributes),ctypes.sizeof(attributes)):
            raise ctypes.WinError(ctypes.get_last_error())
        if attributes.attributes&0x400:raise ValueError('reparse handle is not eligible for code caching')
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
                or tuple(c.cell_contents for c in fn.__closure__ or ())!=self._wrapper_closure
                or _key is not self._key_function or _key.__code__ is not self._key_code
                or self._data is not self._bound_data or self._read is not self._restore_read
                or self._guard is not self._bound_guard):
            raise ValueError('code lease read dispatch changed')
        if (Path.open is not self._cached_open
                or self._cached_open.__code__ is not self._open_code
                or self._cached_open.__defaults__!=self._open_defaults
                or self._cached_open.__kwdefaults__!=self._open_keywords):
            raise ValueError('code lease open dispatch changed')
        if _CodeBytes is not self._view_type or any(getattr(_CodeBytes,name) is not value for name,value in self._view_methods):
            raise ValueError('code byte view dispatch changed')
        for code,(function,module) in self._readers.items():
            if function.__code__ is not code or getattr(module,'read_stable',None) is not function:
                raise ValueError('bound code reader changed')

    def bind_readers(self,functions):
        """Bind exact loaded reader code once, before the measured operation."""
        with self._guard:
            self._check_hooks()
            if not self._code_views or self._readers:raise ValueError('single reader binding required')
            for fn in functions:
                module=sys.modules.get(fn.__module__)
                if (fn.__name__!='read_stable' or module is None
                        or getattr(module,'read_stable',None) is not fn
                        or _key(Path(fn.__code__.co_filename)) not in self._data):
                    raise ValueError('exact pinned read_stable helper required')
                self._readers[fn.__code__]=(fn,module)

    def _view_closed(self):
        with self._guard:self._open_views-=1

    def _fd(self,key):
        if key not in self._fds:
            process=_kernel.GetCurrentProcess();copied=wintypes.HANDLE()
            handle=self._files[Path(key)] if Path(key) in self._files else next(
                h for p,h in self._files.items() if _key(p)==key)
            if not _kernel.DuplicateHandle(process,handle,process,ctypes.byref(copied),0,False,2):
                raise ctypes.WinError(ctypes.get_last_error())
            try:self._fds[key]=msvcrt.open_osfhandle(copied.value,os.O_RDONLY|os.O_BINARY)
            except BaseException:_kernel.CloseHandle(copied);raise
        return self._fds[key]

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
                owner=self;guard=self._guard;cached=self._data;key_function=_key;original=self._read
                original_open=self._restore_open
                self._bound_guard=guard;self._bound_data=cached
                self._key_function=key_function;self._key_code=key_function.__code__
                def read(path):
                    with guard:
                        owner._check_hooks()
                        key=key_function(path);raw=cached.get(key)
                        if raw is not None:
                            owner.hits+=1
                            owner._hits_by_path[key]=owner._hits_by_path.get(key,0)+1
                            return raw
                        owner.fallback_reads+=1
                    return original(path)
                def open_(path,mode='r',buffering=-1,encoding=None,errors=None,newline=None):
                    with guard:
                        owner._check_hooks()
                        key=key_function(path);raw=cached.get(key)
                        frame=sys._getframe(1);binding=owner._readers.get(frame.f_code)
                        if (owner._code_views and binding is not None and frame.f_globals is vars(binding[1])
                                and raw is not None and mode=='rb' and buffering==-1
                                and encoding is None and errors is None and newline is None):
                            fd=owner._fd(key);owner.code_view_hits+=1;owner._open_views+=1
                            owner._hits_by_path[key]=owner._hits_by_path.get(key,0)+1
                            return _CodeBytes(raw,fd,owner._view_closed)
                    return original_open(path,mode,buffering,encoding,errors,newline)
                self._cached_read=read
                self._cached_open=open_ if self._code_views else original_open
                self._open_code=self._cached_open.__code__;self._open_defaults=self._cached_open.__defaults__
                self._open_keywords=self._cached_open.__kwdefaults__
                self._wrapper_code=read.__code__;self._wrapper_defaults=read.__defaults__
                self._wrapper_keywords=read.__kwdefaults__
                self._wrapper_closure=tuple(c.cell_contents for c in read.__closure__ or ())
                if Path.read_bytes is not self._read:
                    raise ValueError('read dispatch changed during lease acquisition')
                Path.read_bytes=read
                if self._code_views:Path.open=open_
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
                hits_by_path=dict(self._hits_by_path),
                file_count=len(self._paths),code_read_hits=self.hits,
                lease_backed_code_byte_view=self._code_views,code_view_hits=self.code_view_hits,
                source_reads_and_fstat_checks_preserved=True,
                fallback_reads=self.fallback_reads,held_handles=len(self._handles),
                source_or_result_cache=False,numerical_result_cache=False,
                distribution_discovery_cached=False,package_versions_cached=False,formal_result=False)

    def _release(self):
        errors=[]
        for fd in self._fds.values():
            try:os.close(fd)
            except OSError as error:errors.append(str(error))
        self._fds.clear()
        for handle in reversed(self._handles):
            if not _kernel.CloseHandle(handle):errors.append(ctypes.get_last_error())
        self._handles.clear();self._state='closed'
        if errors:raise OSError('code lease handle release failed: '+repr(errors))

    def __exit__(self,kind,value,tb):
        with self._guard:
            try:
                self._check_hooks()
                if self._open_views:raise ValueError('code byte views still open at lease release')
                for path in self._paths:
                    current=path.stat(follow_symlinks=False)
                    if ((current.st_dev,current.st_ino)!=self._identities[path]
                            or self._read(path)!=self._data[_key(path)]
                            or _bytes(self._files[path],self._max_bytes)!=self._data[_key(path)]):
                        raise ValueError('code lease bytes or pathname identity changed')
            finally:
                Path.read_bytes=self._restore_read
                Path.open=self._restore_open
                self._release()
