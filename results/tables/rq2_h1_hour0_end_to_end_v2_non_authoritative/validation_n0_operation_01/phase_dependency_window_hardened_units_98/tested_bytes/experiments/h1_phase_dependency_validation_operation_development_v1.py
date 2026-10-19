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
import sys
from threading import Lock, get_ident
from types import MappingProxyType, FunctionType
from weakref import WeakKeyDictionary

from experiments import h1_canonical_path_lease_development_v1 as handles
from experiments import h1_phase_dependency_verifier_development_v1 as predecessor
from experiments import h1_validation_runtime_closure_development_v1 as runtime


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


def _counted_inventory(read):
    """Keep every original inventory read, including duplicate baseline paths."""
    m=predecessor;prior=m.prior;s=prior.symbolic;proof=s.proof;root=prior.ROOT;io=m.io
    baseline_path=root/s.BASELINE;baseline=read(baseline_path,proof.CAP)
    if io.digest(baseline[0])!=s.BASELINE_PIN:raise ValueError('baseline pin differs')
    names=[(root/s.PROOF,s.PROOF_PIN),(Path(s.__file__),None),
        (Path(proof.__file__),None),(baseline_path,s.BASELINE_PIN)]
    names += [(root/name,pin) for name,pin in json.loads(baseline[0])['files_sha256'].items()]
    names += [(root/prior.PROTOCOL,prior.PROTOCOL_PIN),(Path(prior.__file__),None)]
    if len(names)>m.MAX_FILES:raise ValueError('dependency inventory exceeds bound')
    views={baseline_path:baseline};total=len(baseline[0])
    for path,pin in names:
        view=read(path,proof.exclusion.INPUT_CAP)
        if pin is not None and io.digest(view[0])!=pin:raise ValueError('pinned dependency differs')
        if path in views:
            if views[path]!=view:raise ValueError('repeated dependency observation differs')
        else:
            total+=len(view[0])
            if total>m.TOTAL_CAP:raise ValueError('dependency total exceeds bound')
        views[path]=view
    return views


def _scientific_fields(reference):
    # The old freshness/schema/authority statements are private shape references.
    # They are never returned as the current observation's execution facts.
    return {name:reference[name] for name in ('predecessor_group','dependency_sha256',
        'observed_file_count','observed_total_bytes','verifier_sha256',
        'verifier_implementation','verifier_implementation_sha256')}


def _private_api(api):
    """Independent C call objects keep cleanup immune to public ABI mutation."""
    result=[]
    for name in ('CreateFileW','CloseHandle','GetFileInformationByHandleEx'):
        function=getattr(api,name)
        if isinstance(function,ctypes._CFuncPtr):
            prototype=ctypes.WINFUNCTYPE(function.restype,*function.argtypes,use_last_error=True)
            function=prototype(ctypes.cast(function,ctypes.c_void_p).value)
        result.append(function)
    return tuple(result)


def _capsule(plan,check_runtime):
    """Only private closure state owns resources, counters and the fixed plan."""
    error_type=BaseException;describe_error=BaseException.__repr__;add_note=BaseException.add_note
    pid_of,thread_of=os.getpid,get_ident
    creator=(pid_of(),thread_of());guard=Lock()
    create_file,close_file,information=_private_api(handles._kernel_api())
    api=type('PrivateInformationAPI',(),{'GetFileInformationByHandleEx':staticmethod(information)})()
    read_original=predecessor.read_stable;encode=predecessor.io.encode;decode=json.loads
    state='new';first_error=None;first_failure=None;calls=0
    opened=[];pending=set();entries=();views=MappingProxyType({});dependencies=()
    executions=[];cleanup_errors=[];reads_attempted=reads_succeeded=read_bytes=0
    checks_attempted=checks_succeeded=0;rounds_started=rounds_completed=0
    entry_validated=exit_validated=False;identity=implementation_identity()
    plan_sha=sha256(encode(plan)).hexdigest();inventory_paths=0

    def describe(error):
        try:return describe_error(error)
        except error_type:return '<exception description unavailable>'

    def poison(error):
        nonlocal first_error,first_failure
        if first_error is None:first_error=error;first_failure=describe(error)

    def note(primary,error,label):
        try:add_note(primary,label+describe(error))
        except error_type:pass

    def thread():
        if creator!=(pid_of(),thread_of()):raise ValueError('phase operation requires creating thread')

    def read(path,cap):
        nonlocal reads_attempted,reads_succeeded,read_bytes
        reads_attempted+=1
        value=read_original(path,cap)
        reads_succeeded+=1;read_bytes+=len(value[0])
        return value

    def observe(*,allow_failed=False):
        nonlocal checks_attempted,checks_succeeded
        check_runtime();predecessor._scope()
        if (state!='active' or not guard.locked() or first_error is not None and not allow_failed
                or implementation_identity()!=identity):
            raise ValueError('phase observation lifetime changed')
        for path,handle,directory,before in entries:
            checks_attempted+=1
            current=_plain(path,directory=directory)
            actual,attributes=_handle_identity(api,handle)
            if (handle not in pending or actual!=before[:2] or current[:3]!=before[:3]
                    or attributes&0x400 or not directory and current!=before):
                raise ValueError('held phase input or ancestor changed')
            checks_succeeded+=1

    def open_path(path,directory):
        before=_plain(path,directory=directory)
        handle=create_file(str(path),0x81 if directory else 0x80000000,1,None,3,
            0x02200000 if directory else 0x00200080,None)
        if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
        opened.append((path,handle));pending.add(handle)
        actual,attributes=_handle_identity(api,handle);after=_plain(path,directory=directory)
        if actual!=before[:2] or after[:2]!=before[:2] or attributes&0x400:
            raise ValueError('phase path changed during immutable acquisition')
        return path,handle,directory,after

    def release():
        nonlocal state,views,entries
        for path,handle in reversed(opened):
            if handle not in pending:continue
            try:
                if not close_file(handle):raise OSError('phase CloseHandle failed')
                pending.remove(handle)
            except error_type as error:
                poison(error);cleanup_errors.append(describe(error))
                if first_error is not error:note(first_error,error,'phase cleanup: ')
        state='cleanup_pending' if pending else 'closed'
        if not pending:
            views=MappingProxyType({});entries=()
            if guard.locked():guard.release()

    def close(body_error=None):
        nonlocal state,rounds_started,rounds_completed,exit_validated
        thread()
        if state=='closed':return
        if state=='cleanup_pending':
            release()
            if pending:raise first_error
            return
        if body_error is not None:poison(body_error)
        try:
            check_runtime()
            if state!='active':raise ValueError('complete entered phase window required')
            observe(allow_failed=True)
            if calls!=len(plan):raise ValueError('complete fixed phase request plan required')
            rounds_started+=1
            for path,view in views.items():
                if read(path,predecessor.TOTAL_CAP)!=view:
                    raise ValueError('phase input differs at physical exit')
            rounds_completed+=1;exit_validated=True
        except error_type as error:
            poison(error)
            if first_error is not error:note(first_error,error,'phase exit verification: ')
        finally:release()
        if body_error is None and first_error is not None:raise first_error

    def enter():
        nonlocal state,views,dependencies,entries,rounds_started,rounds_completed
        nonlocal entry_validated,inventory_paths
        thread()
        if state!='new' or not guard.acquire(False):
            error=ValueError('single-use nonreentrant phase window required');poison(error);raise error
        state='acquiring'
        try:
            check_runtime();predecessor._scope();rounds_started+=1
            inventory=_counted_inventory(read);dependencies=tuple(inventory)
            for module in (predecessor,predecessor.prior,predecessor.prior.symbolic,
                    predecessor.prior.symbolic.proof,predecessor.io):
                path=Path(module.__file__)
                if path not in inventory:inventory[path]=read(path,predecessor.TOTAL_CAP)
            if len(inventory)>predecessor.MAX_FILES or sum(len(raw) for raw,_ in inventory.values())>predecessor.TOTAL_CAP:
                raise ValueError('complete bounded phase inventory required')
            rounds_completed+=1
            directories={parent for path in inventory for parent in path.parents}
            acquired=[]
            for path in sorted(directories,key=lambda p:(len(p.parts),str(p))):
                acquired.append(open_path(path,True))
            for path in inventory:acquired.append(open_path(path,False))
            rounds_started+=1
            for path,view in inventory.items():
                if read(path,predecessor.TOTAL_CAP)!=view:
                    raise ValueError('phase inventory changed before immutable window')
            rounds_completed+=1
            views=MappingProxyType(inventory);entries=tuple(acquired);inventory_paths=len(views)
            entry_validated=True;state='active';observe()
        except error_type as error:
            poison(error);release();raise

    def prepare(family,ordinal):
        nonlocal calls
        thread()
        try:
            observe()
            if (type(family) is not str or type(ordinal) is not int or calls>=len(plan)
                    or (family,ordinal)!=plan[calls]):
                raise ValueError('exact next declared phase request required')
            reference=_projection(views,dependencies,family,ordinal)
            reference_sha=sha256(encode(reference)).hexdigest()
            science=_scientific_fields(reference);observe()
            calls+=1
            execution=dict(prepare=calls,family=family,ordinal=ordinal,
                legacy_shape_reference_sha256=reference_sha,scientific_projection_only=True)
            executions.append(encode(execution))
            return encode(dict(schema=SCHEMA,active_implementation=identity,plan_sha256=plan_sha,
                scientific_projection=science,execution=execution,observation_schedule='held_entry_exit',
                fresh_at_return_only=False,per_call_physical_freshness=False,
                canonical_physical_verifier_invoked=False,canonical_equivalence_verified=False,
                between_bookend_ABA_covered=False,diagnostic_only=True,consumer_bound=False,
                detached_data=True,**FLAGS))
        except error_type as error:poison(error);raise

    def receipt():
        thread();check_runtime()
        return dict(schema=SCHEMA,active_implementation=identity,diagnostic_only=True,
            consumer_bound=False,detached_data=True,observation_schedule='held_entry_exit',
            per_call_physical_freshness=False,between_bookend_ABA_covered=False,
            canonical_equivalence_verified=False,plan_sha256=plan_sha,declared_plan=decode(encode(plan)),
            maximum_prepares=len(plan),completed_prepares=calls,executions=[decode(raw) for raw in executions],
            inventory_paths=inventory_paths,physical_read_attempts=reads_attempted,
            physical_reads_succeeded=reads_succeeded,physical_bytes_read=read_bytes,
            inventory_rounds_started=rounds_started,inventory_rounds_completed=rounds_completed,
            held_inventory_projections=calls,path_handle_checkpoint_attempts=checks_attempted,
            completed_path_handle_checkpoints=checks_succeeded,first_failure=first_failure,
            cleanup_errors=list(cleanup_errors),entry_physical_validation_completed=entry_validated,
            exit_physical_validation_completed=exit_validated,state=state,closed=state=='closed',
            pending_handles=len(pending),all_handles_closed=not pending,immutable_bytes_cleared=not views,
            original_guard_released=not guard.locked(),lifecycle_complete=(state=='closed'
                and first_error is None and not pending and calls==len(plan)
                and entry_validated and exit_validated),**FLAGS)

    return enter,prepare,close,receipt


def _define_api(check_runtime):
    records=WeakKeyDictionary();build=_capsule
    class PhaseDependencyValidationOperation:
        """Single-use detached data window; no writable working/resource fields."""
        __slots__=('__weakref__',)

        def __init__(self,*,plan,diagnostic_only):
            check_runtime()
            if self in records:raise ValueError('phase operation cannot be reinitialized')
            if (os.name!='nt' or diagnostic_only is not True or type(plan) is not tuple
                    or not 1<=len(plan)<=MAX_PREPARES or any(type(row) is not tuple or len(row)!=2
                        or type(row[0]) is not str or row[0] not in predecessor.prior.symbolic.proof.MISSING
                        or type(row[1]) is not int or row[1]<0 for row in plan)):
                raise ValueError('exact bounded immutable diagnostic phase plan required')
            records[self]=build(plan,check_runtime)

        def __enter__(self):
            records[self][0]();return self

        def prepare_group(self,family,ordinal):
            return records[self][1](family,ordinal)

        def close(self):
            return records[self][2]()

        def retry_cleanup(self):
            return records[self][2]()

        def __exit__(self,kind,value,traceback):
            records[self][2](value)

        def receipt(self):
            return records[self][3]()

        def __copy__(self):raise TypeError('phase data window cannot be copied')
        def __deepcopy__(self,memo):raise TypeError('phase data window cannot be copied')
        def __reduce_ex__(self,protocol):raise TypeError('phase data window cannot be serialized')
    return PhaseDependencyValidationOperation


_RUNTIME,_ARM=runtime.make_runtime(globals(),'phase dependency data operation',alias='_RUNTIME')
PhaseDependencyValidationOperation=_define_api(_RUNTIME)
_CANONICAL_MODULES=tuple((module.__name__,module) for module in
    (sys.modules[__name__],predecessor,predecessor.prior,predecessor.prior.symbolic,
        predecessor.prior.symbolic.proof,predecessor.io,handles,runtime))


def _module_routes():
    if any(sys.modules.get(name) is not module for name,module in _CANONICAL_MODULES):
        raise ValueError('canonical phase operation module registry changed')


def _dependency_attributes():
    attributes=[];m=predecessor;prior=m.prior;s=prior.symbolic;p=s.proof;io=m.io
    for owner,names in ((m,('read_stable','_views','_scope','prepare_group','prior','io','__file__')),
            (prior,('_project','SCHEMA','PROTOCOL_PIN','FLAGS','ROOT','symbolic')),
            (s,('PROOF','PROOF_PIN','BASELINE','BASELINE_PIN','proof','io','__file__')),
            (p,('_resolver','_node','Resolver','CAP','MISSING','CATALOG_PIN','SCHEMA','io')),
            (io,('digest','encode','identity')), (json,('loads',)),
            (handles,('_kernel_api','_FileId','_Attributes')),
            (Path,('stat','open')), (os,('getpid','stat','fstat')),
            (stat,('S_ISDIR','S_ISREG')),
            (ctypes,('WINFUNCTYPE','WinDLL','_CFuncPtr','c_void_p','cast','byref','sizeof','get_last_error','WinError'))):
        attributes.extend((owner,name,getattr(owner,name)) for name in names)
    for _,module in _CANONICAL_MODULES:
        attributes.extend((module,name,getattr(module,name)) for name in
            ('__name__','__file__','__spec__','__loader__','__package__'))
        if module.__spec__ is not None:
            attributes.extend((module.__spec__,name,getattr(module.__spec__,name))
                for name in ('name','origin','loader'))
        if module.__loader__ is not None:
            attributes.extend((module.__loader__,name,getattr(module.__loader__,name))
                for name in ('name','path') if hasattr(module.__loader__,name))
    for owner in (PhaseDependencyValidationOperation,p.Resolver):
        attributes.extend((owner,name,value) for name,value in vars(owner).items()
            if isinstance(value,(FunctionType,property,staticmethod,classmethod)))
    return tuple(attributes)


_ARM(attributes=_dependency_attributes(),checks=(_module_routes,),ignored=('_ARM',))
del _ARM
