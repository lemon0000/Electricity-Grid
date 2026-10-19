"""Diagnostic phase-data window with immutable Windows handles and new identity.

The predecessor JSON is a byte projection only. This operation is not a
Bootstrap/Roster capability and does not replace any existing verifier route.
"""
from hashlib import sha256
import ctypes
import json
import os
from pathlib import Path
import stat
from threading import Lock, get_ident
from types import MappingProxyType

from experiments import h1_canonical_path_lease_development_v1 as handles
from experiments import h1_phase_dependency_verifier_development_v1 as predecessor


SCHEMA='h1_phase_dependency_validation_operation_development_v1'
MAX_PREPARES=16
FLAGS=dict(formal_result=False,formal_execution_ready=False,resource_admission=False,
    native_execution_authorized=False,owner_consumption_authorized=False)


def implementation_identity():
    return sha256(predecessor.io.encode([SCHEMA,sha256(Path(__file__).read_bytes()).hexdigest(),
        sha256(Path(predecessor.__file__).read_bytes()).hexdigest(),
        sha256(Path(handles.__file__).read_bytes()).hexdigest()])).hexdigest()


def _metadata(path):
    value=path.stat(follow_symlinks=False)
    return (value.st_dev,value.st_ino,value.st_mode,value.st_size,value.st_mtime_ns,
        value.st_ctime_ns,value.st_nlink,value.st_file_attributes)


def _handle_identity(api,handle):
    value=handles._FileId()
    if not api.GetFileInformationByHandleEx(handle,18,ctypes.byref(value),ctypes.sizeof(value)):
        raise ctypes.WinError(ctypes.get_last_error())
    attributes=handles._Attributes()
    if not api.GetFileInformationByHandleEx(handle,9,ctypes.byref(attributes),ctypes.sizeof(attributes)):
        raise ctypes.WinError(ctypes.get_last_error())
    return (value.volume,int.from_bytes(value.file_id,'little')),attributes.attributes


def _plain(path,*,directory):
    value=_metadata(path)
    if (value[7]&0x400 or not (stat.S_ISDIR(value[2]) if directory else stat.S_ISREG(value[2]))
            or not directory and value[6]!=1):
        raise ValueError('plain non-reparse, single-link phase input required')
    return value


def _projection(views,dependency_paths,family,ordinal):
    """Mechanical predecessor projection over an already authenticated inventory."""
    m=predecessor;io=m.io;prior=m.prior;root=prior.ROOT
    pins={(p.relative_to(root).as_posix() if p.is_relative_to(root) else p.as_posix()):
        io.digest(views[p][0]) for p in dependency_paths}
    own=views[Path(m.__file__)][0]
    implementation=dict(schema=m.SCHEMA,verifier_sha256=io.digest(own),
        predecessor_files_sha256={Path(module.__file__).as_posix():io.digest(views[Path(module.__file__)][0])
            for module in (prior,prior.symbolic,prior.symbolic.proof,io)})
    group=prior._project(views[root/prior.symbolic.PROOF][0],family,ordinal,io.digest(io.encode(pins)))
    return dict(schema=m.SCHEMA,verifier_sha256=io.digest(own),verifier_implementation=implementation,
        verifier_implementation_sha256=io.digest(io.encode(implementation)),predecessor_group=group,
        dependency_sha256=pins,observed_file_count=len(pins),
        observed_total_bytes=sum(len(views[p][0]) for p in dependency_paths),
        fresh_at_return_only=True,detached_data=True,**m.FLAGS)


class PhaseDependencyValidationOperation:
    """One creating thread, fixed finite plan, full physical entry and exit reads.

    Internal prepares retain complete path/handle checks and immutable bytes.
    The different observation schedule is explicitly named in the new receipt.
    No existing owner or canonical verifier is patched by this diagnostic.
    """
    def __init__(self,*,maximum_prepares,diagnostic_only):
        if (os.name!='nt' or diagnostic_only is not True or type(maximum_prepares) is not int
                or not 1<=maximum_prepares<=MAX_PREPARES):
            raise ValueError('explicit bounded Windows diagnostic-only phase window required')
        self._creator=(os.getpid(),get_ident())
        self._guard=self._original_guard=Lock()
        self._maximum=self._fixed_maximum=maximum_prepares
        self._state='new';self._failure=None;self._calls=0
        self._api=handles._kernel_api()
        self._opened=[];self._entries=MappingProxyType({});self._views=MappingProxyType({})
        self._dependencies=();self._executions=[];self._cleanup_errors=[]
        self._physical_reads=0;self._logical_views=0;self._checkpoint_views=0
        self._identity=implementation_identity()

    def _poison(self,error):
        if self._failure is None:self._failure=repr(error)

    def _open(self,path,*,directory):
        before=_plain(path,directory=directory)
        # Directories include data-read access so share restrictions are effective.
        # Files deny both writes and deletion; all ancestors are retained too.
        handle=self._api.CreateFileW(str(path),0x81 if directory else 0x80000000,
            1,None,3,0x02200000 if directory else 0x00200080,None)
        if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
        self._opened.append((path,handle))
        actual,attributes=_handle_identity(self._api,handle)
        after=_plain(path,directory=directory)
        if actual!=before[:2] or after[:2]!=before[:2] or attributes&0x400:
            raise ValueError('phase path changed during immutable acquisition')
        return (path,handle,directory,after)

    def __enter__(self):
        if self._state!='new' or not self._guard.acquire(False):
            raise ValueError('single-use nonreentrant phase window required')
        try:
            predecessor._scope()
            views=predecessor._views();self._physical_reads+=len(views)
            self._dependencies=tuple(views)
            for module in (predecessor,predecessor.prior,predecessor.prior.symbolic,
                    predecessor.prior.symbolic.proof,predecessor.io):
                path=Path(module.__file__)
                if path not in views:
                    views[path]=predecessor.read_stable(path,predecessor.TOTAL_CAP)
                    self._physical_reads+=1
            if len(views)>predecessor.MAX_FILES or sum(len(raw) for raw,_ in views.values())>predecessor.TOTAL_CAP:
                raise ValueError('complete bounded phase inventory required')
            directories={parent for path in views for parent in path.parents}
            entries={}
            for path in sorted(directories,key=lambda p:(len(p.parts),str(p))):
                entries[str(path)]=self._open(path,directory=True)
            for path in views:entries[str(path)]=self._open(path,directory=False)
            for path,view in views.items():
                if predecessor.read_stable(path,predecessor.TOTAL_CAP)!=view:
                    raise ValueError('phase inventory changed before immutable window')
                self._physical_reads+=1
            self._entries=self._original_entries=MappingProxyType(entries)
            self._views=self._original_views=MappingProxyType(views)
            self._state='active';self._check()
            return self
        except BaseException as error:
            self._poison(error)
            self.close(error)
            raise

    def _check(self):
        predecessor._scope()
        if (self._state!='active' or self._failure is not None
                or self._creator!=(os.getpid(),get_ident()) or self._guard is not self._original_guard
                or not self._original_guard.locked() or self._maximum!=self._fixed_maximum
                or self._entries is not self._original_entries or self._views is not self._original_views
                or implementation_identity()!=self._identity):
            raise ValueError('phase observation lifetime changed')
        for path,handle,directory,before in self._entries.values():
            current=_plain(path,directory=directory)
            actual,attributes=_handle_identity(self._api,handle)
            if (actual!=before[:2] or current[:3]!=before[:3] or attributes&0x400
                    or not directory and current!=before):
                raise ValueError('held phase input or ancestor changed')
            self._checkpoint_views+=1

    def prepare_group(self,family,ordinal):
        try:
            self._check()
            if (type(family) is not str or family not in predecessor.prior.symbolic.proof.MISSING
                    or type(ordinal) is not int or ordinal<0 or self._calls>=self._maximum):
                raise ValueError('bounded exact phase request required')
            projected=_projection(self._views,self._dependencies,family,ordinal)
            raw=predecessor.io.encode(projected)
            self._check()
            self._calls+=1;self._logical_views+=2*len(self._views)
            execution=dict(prepare=self._calls,family=family,ordinal=ordinal,
                canonical_predecessor_payload_sha256=sha256(raw).hexdigest(),
                scientific_projection_only=True,canonical_physical_verifier_invoked=False)
            self._executions.append(execution)
            return predecessor.io.encode(dict(schema=SCHEMA,active_implementation=self._identity,
                canonical_predecessor_payload=projected,execution=execution,
                diagnostic_only=True,consumer_bound=False,detached_data=True,**FLAGS))
        except BaseException as error:
            self._poison(error)
            raise

    def close(self,body_error=None):
        if (os.getpid(),get_ident())!=self._creator:
            raise ValueError('phase cleanup requires creating thread')
        if self._state=='closed':return
        error=body_error
        if body_error is not None:self._poison(body_error)
        try:
            if self._state=='active':
                self._check()
                if self._calls!=self._fixed_maximum:
                    raise ValueError('complete fixed phase prepare plan required')
            for path,view in self._views.items():
                if predecessor.read_stable(path,predecessor.TOTAL_CAP)!=view:
                    raise ValueError('phase input differs at physical exit')
                self._physical_reads+=1
        except BaseException as failure:
            self._poison(failure)
            if error is None:error=failure
            else:error.add_note('phase exit verification: '+repr(failure))
        finally:
            failed=[]
            for path,handle in reversed(self._opened):
                try:
                    if not self._api.CloseHandle(handle):raise ctypes.WinError(ctypes.get_last_error())
                except BaseException as failure:
                    failed.append((path,handle));self._cleanup_errors.append(repr(failure))
                    self._poison(failure)
                    if error is None:error=failure
                    else:error.add_note('phase handle cleanup: '+repr(failure))
            self._opened=list(reversed(failed));self._state='closed'
            self._entries=MappingProxyType({});self._views=MappingProxyType({})
            if self._original_guard.locked():self._original_guard.release()
        if body_error is None and error is not None:raise error

    def __exit__(self,kind,value,traceback):
        self.close(value)

    def receipt(self):
        return dict(schema=SCHEMA,active_implementation=self._identity,diagnostic_only=True,
            consumer_bound=False,detached_data=True,maximum_prepares=self._fixed_maximum,
            completed_prepares=self._calls,executions=json.loads(predecessor.io.encode(self._executions)),
            physical_file_reads=self._physical_reads,logical_file_views=self._logical_views,
            path_and_handle_checkpoints=self._checkpoint_views,first_failure=self._failure,
            cleanup_errors=list(self._cleanup_errors),closed=self._state=='closed',
            all_handles_closed=not self._opened,immutable_bytes_cleared=not self._views,
            original_guard_released=not self._original_guard.locked(),
            complete=(self._state=='closed' and self._failure is None and not self._opened
                and self._calls==self._fixed_maximum),**FLAGS)
