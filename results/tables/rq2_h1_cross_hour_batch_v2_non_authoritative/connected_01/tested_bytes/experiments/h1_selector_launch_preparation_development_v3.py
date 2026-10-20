"""Read-only selector launch declarations. No spawn, lease or execution authority."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import stat
import sys
from types import MappingProxyType,ModuleType

from experiments import h1_selector_released_worker_development_v3 as worker

io,process=worker.io,worker.process
resources=process.resources
SCHEMA='h1_selector_launch_preparation_development_v3'
PARENT_BYTES=5*1024**2+1  # binding 1 MiB, terminal 4 MiB, lease byte
FLAGS=MappingProxyType(dict(worker.FLAGS,selector_parent_connected=False,
    resource_admission=False,non_solver_allowance_verified=False,native_execution_authorized=False))
_FLAGS=FLAGS
_KEYS=frozenset(FLAGS)
_REPO=Path(__file__).resolve().parents[1]
_PYTHON=Path(sys.executable).resolve()
# All variable values travel as argv data; no path or request text is executable.
_SCRIPT='''import sys
from pathlib import Path
repo=Path(sys.argv[1])
sys.path.insert(0,str(repo))
from experiments import h1_selector_released_worker_development_v3 as worker
if Path(worker.__file__).resolve()!=repo/'experiments'/'h1_selector_released_worker_development_v3.py':
    raise ValueError('selector worker import path differs')
if worker.implementation_identity()!=sys.argv[2]:
    raise ValueError('selector worker implementation differs')
worker.execute(sys.argv[3],sys.argv[4])
'''
_SCRIPT_BYTES=_SCRIPT.encode('ascii')


def _verify():
    if (SCHEMA!='h1_selector_launch_preparation_development_v3'
            or type(PARENT_BYTES) is not int or PARENT_BYTES!=5*1024**2+1
            or FLAGS is not _FLAGS or frozenset(FLAGS)!=_KEYS or any(v is not False for v in FLAGS.values())
            or _SCRIPT.encode('ascii')!=_SCRIPT_BYTES or _REPO!=Path(__file__).resolve().parents[1]
            or Path(sys.executable).resolve()!=_PYTHON
            or any(getattr(obj,name) is not original for obj,name,original in _FIXED)
            or any(vars(obj).get(name) is not original for obj,name,original in _SOURCE_FIXED)
            or _protocol_scope()!=_PROTOCOL_SCOPE):
        raise ValueError('selector launch preparation scope changed')


def implementation_identity():
    _CHECK()
    return io.digest(io.encode([SCHEMA,__name__,io.digest(Path(__file__).read_bytes()),
        str(_REPO),worker.implementation_identity()]))


def _positive(value):
    if type(value) is not int or not 0<value<=2**63-1:
        raise ValueError('bounded positive resource bytes required')


def _executable(path):
    # Conda executables may be hardlinked to its package cache. Evidence-file
    # single-link rules do not apply; retain nlink and all stable stat fields.
    resources.local._path(path)
    def stamp(s):
        if not stat.S_ISREG(s.st_mode) or getattr(s,'st_file_attributes',0)&1024:
            raise ValueError('plain Python executable required')
        return (s.st_dev,s.st_ino,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    before=stamp(path.stat(follow_symlinks=False))
    if not 0<before[3]<=256*1024**2:raise ValueError('bounded Python executable required')
    with path.open('rb') as stream:
        opened=stamp(os.fstat(stream.fileno()))
        # Windows hardlink path and handle creation times can differ. Compare
        # identity/content metadata across views, and each full stamp to itself.
        if opened[:5]!=before[:5]:raise ValueError('Python executable changed before read')
        raw=stream.read(256*1024**2+1)
        if stamp(os.fstat(stream.fileno()))!=opened:raise ValueError('Python executable changed during read')
    if len(raw)!=before[3] or stamp(path.stat(follow_symlinks=False))!=before:
        raise ValueError('Python executable changed after read')
    return raw,before


def _path(value):
    path=worker.sequence.legacy._root(value)
    # Reject existing symlink/reparse ancestors even before directories exist.
    for entry in (path,*path.parents):
        if entry.exists():resources.local._path(entry)
    if not path.name.endswith('_non_authoritative'):
        raise ValueError('non-authoritative parent root required')
    return path


def prepare(root,snapshot_bytes,*,max_timing_archive_bytes,scratch_bytes,
            parent_extra_commit_bytes,commit_reserve_bytes,disk_reserve_bytes):
    """Pure declaration; may precede mkdir. Rebuild source and retain exact bytes.

    A later parent must create-once persist its binding, make directories, call
    bind, and own the lifecycle. This declaration is freely constructible data.
    """
    check,identify=_CHECK,_IDENTITY
    check();own=identify()
    root=_path(root)
    for value in (scratch_bytes,parent_extra_commit_bytes,commit_reserve_bytes,disk_reserve_bytes):
        _positive(value)
    job=root/'worker_non_authoritative';scratch=job/'scratch_non_authoritative'
    with worker.sequence.legacy.bridge.science.prior.guard.solver_calls_forbidden():
        request=worker.request_document(job,snapshot_bytes,max_timing_archive_bytes=max_timing_archive_bytes)
        budget=process.TaskProcessBudget(**request['budget'])
        request_pin=io.digest(io.encode(request))
        executable=_PYTHON
        if not executable.is_file():raise ValueError('existing Python executable required')
        executable_raw,executable_stamp=_executable(executable)
        environment=worker.runtime.development_environment()
        environment.update(TEMP=str(scratch),TMP=str(scratch))
        worker.runtime._environment(environment)
        host=resources.HostResourceBudget(budget.max_job_commit_bytes+parent_extra_commit_bytes,
            commit_reserve_bytes,(
                resources.DirectoryDemand('selector',str(job),worker.content_bound(request),disk_reserve_bytes),
                resources.DirectoryDemand('scratch',str(scratch),scratch_bytes,disk_reserve_bytes),
                resources.DirectoryDemand('parent',str(root),PARENT_BYTES,disk_reserve_bytes)))
        for demand in host.directories:_positive(demand.additional_bytes)
        _positive(host.additional_commit_bytes)
        argv=[str(executable),'-I','-B','-c',_SCRIPT,str(_REPO),worker.implementation_identity(),
            str(job/'request.json'),request_pin]
        # Size-check the eventual exact launch schema using a fixed-size digest.
        launch=dict(request_sha256=request_pin,process_identity='0'*64,argv=argv,cwd=str(scratch),
            environment_sha256=io.digest(io.encode(environment)),budget=asdict(budget),host=asdict(host))
        if len(io.encode(launch))>worker.CAP:raise ValueError('selector launch metadata cap')
        declaration=dict(schema=SCHEMA,implementation=own,root=str(root),request=request,
            request_sha256=request_pin,argv=argv,environment=environment,host=asdict(host),
            executable_sha256=io.digest(executable_raw),executable_stamp=list(executable_stamp),
            scratch_bytes=scratch_bytes,parent_extra_commit_bytes=parent_extra_commit_bytes,
            commit_reserve_bytes=commit_reserve_bytes,disk_reserve_bytes=disk_reserve_bytes,**FLAGS)
        raw=io.encode(declaration)
        if len(raw)>worker.CAP:raise ValueError('selector parent binding metadata cap')
        # Bookend fresh source and implementation; do not return stale preparation.
        if io.encode(worker.request_document(job,snapshot_bytes,
                max_timing_archive_bytes=max_timing_archive_bytes))!=io.encode(request):
            raise ValueError('selector source changed during launch preparation')
        if _executable(executable)!=(executable_raw,executable_stamp):
            raise ValueError('Python executable changed during launch preparation')
    # solver_calls_forbidden legitimately swaps solver entrypoints while active.
    # Check the complete captured closure after its mandatory restoration.
    check()
    if identify()!=own:raise ValueError('selector launch implementation changed')
    return raw


def bind(declaration,snapshot_bytes):
    """Fresh read-only launch identity after directories exist; no headroom claim.

    Reconstruct rather than trust caller data. Return JSON bytes in the existing
    worker launch schema; retained parent pins and Job ownership remain external.
    """
    check,identify,prepare_fixed=_CHECK,_IDENTITY,prepare
    check()
    if type(declaration) is not bytes or not 0<len(declaration)<=worker.CAP:
        raise ValueError('bounded immutable launch declaration required')
    doc=json.loads(declaration)
    if type(doc) is not dict or doc.get('schema')!=SCHEMA or doc.get('implementation')!=identify():
        raise ValueError('canonical launch declaration implementation required')
    root=_path(doc['root'])
    options={k:doc[k] for k in ('scratch_bytes','parent_extra_commit_bytes',
        'commit_reserve_bytes','disk_reserve_bytes')}
    options['max_timing_archive_bytes']=doc['request']['max_timing_archive_bytes']
    if prepare_fixed(root,snapshot_bytes,**options)!=declaration:
        raise ValueError('fresh selector launch declaration differs')
    check()
    host=resources.HostResourceBudget(doc['host']['additional_commit_bytes'],doc['host']['commit_reserve_bytes'],
        tuple(resources.DirectoryDemand(**d) for d in doc['host']['directories']))
    budget=process.TaskProcessBudget(**doc['request']['budget'])
    scratch=root/'worker_non_authoritative'/'scratch_non_authoritative'
    identity=process.task_process_identity(doc['argv'],cwd=scratch,environment=doc['environment'],
        budget=budget,host_budget=host,expected_host_identity=resources.resource_identity(host))
    value=dict(request_sha256=doc['request_sha256'],process_identity=identity,argv=doc['argv'],cwd=str(scratch),
        environment_sha256=io.digest(io.encode(doc['environment'])),budget=asdict(budget),host=asdict(host))
    check()
    if prepare_fixed(root,snapshot_bytes,**options)!=declaration:
        raise ValueError('selector launch declaration changed during binding')
    check()
    again=process.task_process_identity(doc['argv'],cwd=scratch,environment=doc['environment'],
        budget=budget,host_budget=host,expected_host_identity=resources.resource_identity(host))
    if again!=identity:raise ValueError('selector launch directories or process identity changed')
    check()
    return io.encode(value)


def _source_closure():
    """Freeze reachable project callables, module edges and class descriptors.

    Includes helpers imported by name: follow their defining project module as
    well as explicit module references. External library internals are excluded.
    This is an in-process replacement guard, not a hostile-Python sandbox.
    """
    def project(name):return name.startswith(('experiments.','src.'))
    pending=[worker];seen=set();records=[]
    while pending:
        module=pending.pop()
        if id(module) in seen:continue
        seen.add(id(module))
        for name,value in sorted(tuple(vars(module).items())):
            if isinstance(value,ModuleType):
                if project(value.__name__):
                    records.append((module,name,value));pending.append(value)
            elif callable(value):
                records.append((module,name,value))
                origin=getattr(value,'__module__','')
                if project(origin) and origin in sys.modules:pending.append(sys.modules[origin])
                if isinstance(value,type) and project(origin):
                    for member,descriptor in sorted(vars(value).items()):
                        if callable(descriptor) or isinstance(descriptor,(property,staticmethod,classmethod)):
                            records.append((value,member,descriptor))
    return tuple(sorted(records,key=lambda row:(getattr(row[0],'__module__',''),row[0].__name__,row[1])))


def _protocol_scope():
    def plain(value):
        if isinstance(value,(dict,MappingProxyType)):
            return {key:plain(item) for key,item in value.items()}
        if type(value) in (tuple,list):return [plain(item) for item in value]
        if type(value) in (set,frozenset):return sorted(plain(item) for item in value)
        return value
    return io.encode([(module.__name__,{
        name:plain(value) for name,value in sorted(vars(module).items())
        if name.isupper() and not name.startswith('_') and
        (any(token in name for token in ('SCHEMA','CAP','LIMIT','MAX'))
         or name in ('FLAGS','INPUTS','OUTPUTS','PHASES','FILES','INPUT_FILES','OUTPUT_FILES'))
        and not callable(value)}) for module in _PROTOCOL_MODULES])


_SOURCE_FIXED=_source_closure()
_PROTOCOL_MODULES=tuple(sorted({owner for owner,_,_ in _SOURCE_FIXED if isinstance(owner,ModuleType)},
    key=lambda module:module.__name__))
_PROTOCOL_SCOPE=_protocol_scope()
_CHECK,_IDENTITY=_verify,implementation_identity
_FIXED=tuple((obj,name,getattr(obj,name)) for obj,names in (
    (sys.modules[__name__],('prepare','bind','_executable','_path','_positive','_verify','implementation_identity',
        '_source_closure','_protocol_scope','worker','io','process','resources','_PYTHON','_REPO',
        '_SCRIPT_BYTES','_SOURCE_FIXED','_PROTOCOL_MODULES','_PROTOCOL_SCOPE','_CHECK','_IDENTITY')),
    (worker,('request_document','implementation_identity','content_bound','_read')),
    (worker.runtime,('development_environment','_environment')),
    (process,('TaskProcessBudget','task_process_identity')),
    (resources,('DirectoryDemand','HostResourceBudget','resource_identity')),
    (resources.local,('_path',)),
    (io,('encode','digest')),
) for name in names)
