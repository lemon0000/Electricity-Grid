"""Owned selector parent development. Real run requires separate native authority.

No persistent common-phase consumption, reuse credit or formal result is issued.
"""
from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from threading import Lock,get_ident
from types import MappingProxyType,FunctionType
from uuid import uuid4

from experiments import h1_selector_launch_preparation_development_v1 as preparation
from experiments import h1_selector_job_lifecycle_development_v1 as lifecycle
from experiments import h1_selector_worker_output_inspection_development_v1 as inspection

worker,io,process=preparation.worker,preparation.io,preparation.process
local=process.resources.local
SCHEMA='h1_selector_parent_controller_development_v1'
META_CAP=1024**2
TERMINAL_CAP=4*1024**2
FLAGS=MappingProxyType(dict(preparation.FLAGS,owner_consumption_authorized=False,
    parent_phase_commit_verified=False,live_parent_completion_detached_replay=False))
_FLAGS=FLAGS
_KEYS=frozenset(FLAGS)
_TOKEN=object()
_OWNERS={}
_REGISTRY_LOCK=Lock()
_COMPLETION_FIELDS=('root','role','terminal_sha256','scientific_root','scientific_terminal_sha256',
    'scientific_request_sha256','sequence_request_sha256','max_archive_bytes')


def _verify():
    if (SCHEMA!='h1_selector_parent_controller_development_v1' or META_CAP!=1024**2
            or TERMINAL_CAP!=4*1024**2 or FLAGS is not _FLAGS or frozenset(FLAGS)!=_KEYS
            or any(v is not False for v in FLAGS.values())
            or any(vars(obj).get(name) is not value for obj,name,value in _FIXED)
            or tuple(ParentCompletion.__annotations__)!=_COMPLETION_FIELDS
            or _dependency_scope()!=_DEPENDENCY_SCOPE):
        raise ValueError('selector parent scope changed')
    preparation._CHECK()


def implementation_identity():
    _CHECK()
    return io.digest(io.encode([SCHEMA,__name__,io.digest(Path(__file__).read_bytes()),
        preparation.implementation_identity(),lifecycle.implementation_identity(),inspection.implementation_identity()]))


def _same(a,b):
    if io.encode(a)!=io.encode(b):raise ValueError('selector parent correspondence differs')


@dataclass(frozen=True,init=False)
class ParentCompletion:
    root: str
    role: str
    terminal_sha256: str
    scientific_root: str
    scientific_terminal_sha256: str
    scientific_request_sha256: str
    sequence_request_sha256: str
    max_archive_bytes: int

    def __init__(self,values,*,_token=None):
        if _token is not _TOKEN:raise TypeError('live parent-issued completion required')
        for name,value in zip(_COMPLETION_FIELDS,values,strict=True):object.__setattr__(self,name,value)

    def __copy__(self):raise TypeError('parent completion cannot be copied')
    def __deepcopy__(self,memo):raise TypeError('parent completion cannot be copied')
    def __reduce_ex__(self,protocol):raise TypeError('parent completion cannot be serialized')


def _completion_bytes(value):
    if type(value) is not ParentCompletion:raise TypeError('exact parent completion required')
    return io.encode({name:getattr(value,name) for name in _COMPLETION_FIELDS})


class Parent:
    """Create once, run once, retain a same-process/thread completion while open."""
    __slots__=('root','worker_root','_guard','_lease','_pid','_thread','_nonce','_own',
        '_raw','_declaration','_binding','_launch','_options','_seed','_records','_directories',
        '_state','_issued','_issued_bytes','_outcome','_reference_owner','_reference_completion',
        '_reference_descriptor','_reference_held')

    def __init__(self,root,snapshot_bytes,*,max_timing_archive_bytes,scratch_bytes,
                 parent_extra_commit_bytes,commit_reserve_bytes,disk_reserve_bytes,
                 reference_owner=None,reference_completion=None):
        check,identify,cleanup=_CHECK,_IDENTITY,_CLEANUP;check()
        self._guard=Lock();self._lease=None;self._state='constructing';self._issued=None
        self._issued_bytes=None;self._outcome=None;self._reference_held=False
        self._pid,self._thread=os.getpid(),get_ident();self._nonce=uuid4().hex;self._own=identify()
        self.root=preparation._path(root);self.worker_root=self.root/'worker_non_authoritative'
        self._raw=snapshot_bytes
        self._options=dict(max_timing_archive_bytes=max_timing_archive_bytes,scratch_bytes=scratch_bytes,
            parent_extra_commit_bytes=parent_extra_commit_bytes,commit_reserve_bytes=commit_reserve_bytes,
            disk_reserve_bytes=disk_reserve_bytes)
        self._declaration=preparation.prepare(self.root,snapshot_bytes,**self._options)
        self._reference_owner,self._reference_completion=reference_owner,reference_completion
        self._reference_descriptor=self._reference_initial()
        self._binding=io.encode(dict(schema=SCHEMA,implementation=self._own,nonce=self._nonce,
            pid=self._pid,thread_id=self._thread,declaration=json.loads(self._declaration),
            reference_execution=self._reference_descriptor,**FLAGS))
        if len(self._binding)>META_CAP:raise ValueError('selector parent binding cap')
        self._records={};self._launch=None;self._directories=None
        self._seed=self._fingerprint()
        check()
        with _REGISTRY_LOCK:
            if self._nonce in _OWNERS:raise ValueError('selector parent nonce already owned')
            _OWNERS[self._nonce]=self
        try:
            # The parent binding precedes every worker directory and input file.
            self._lease=local._Lease(self.root,True)
            self._keep('binding.json',self._binding,META_CAP)
            self.worker_root.mkdir();(self.worker_root/'scratch_non_authoritative').mkdir()
            self._directories=self._directory_view()
            request=json.loads(self._declaration)['request']
            self._keep('worker_non_authoritative/selector_snapshot.json',snapshot_bytes,worker.snapshot.CAP)
            self._keep('worker_non_authoritative/request.json',io.encode(request),worker.CAP)
            self._launch=preparation.bind(self._declaration,snapshot_bytes)
            self._keep('worker_non_authoritative/launch.json',self._launch,worker.CAP)
            self._state='prepared'
            self._check();self._source()
        except BaseException:
            self._state='failed'
            cleanup(self)
            raise

    def _fingerprint(self):
        return io.encode([str(self.root),str(self.worker_root),self._pid,self._thread,self._nonce,self._own,
            io.digest(self._raw),io.digest(self._declaration),io.digest(self._binding),self._options,
            id(self._guard),id(self._reference_owner),id(self._reference_completion),self._reference_descriptor])

    def _keep(self,name,raw,cap):
        if type(raw) is not bytes or not 0<len(raw)<=cap:raise ValueError('bounded parent record required')
        path=self.root/name;io.write_new(path,raw)
        saved=worker._read(path,cap)
        if saved[0]!=raw:raise ValueError('parent record readback differs')
        self._records[name]=(cap,*saved)

    def _directory_view(self):
        directory=worker.sequence.timed.capture.directory
        return (directory(self.root),directory(self.worker_root),directory(self.worker_root/'scratch_non_authoritative'))

    def _check(self):
        _CHECK()
        if (type(self) is not Parent or self._state not in ('prepared','running','complete')
                or (self._pid,self._thread)!=(os.getpid(),get_ident())
                or _OWNERS.get(self._nonce) is not self or self._fingerprint()!=self._seed
                or _IDENTITY()!=self._own or type(self._lease) is not local._Lease or self._lease.root!=self.root):
            raise ValueError('live original selector parent required')
        self._lease.check()
        names={'execution.lock','binding.json','worker_non_authoritative'}
        if 'terminal.json' in self._records:names.add('terminal.json')
        worker.sequence.legacy.stage._directory(self.root,names)
        if self._directory_view()!=self._directories:raise ValueError('parent directory identity changed')
        for name,(cap,raw,stamp) in self._records.items():
            if worker._read(self.root/name,cap)!=(raw,stamp):raise ValueError('parent retained record changed')
        if self._records['binding.json'][1]!=self._binding:raise ValueError('parent binding changed')

    def _source(self):
        self._check()
        if preparation.prepare(self.root,self._raw,**self._options)!=self._declaration:
            raise ValueError('parent source declaration changed')
        if preparation.bind(self._declaration,self._raw)!=self._launch:
            raise ValueError('parent launch identity changed')
        self._check()

    def _reference_match(self,owner,receipt):
        declaration=json.loads(self._raw);other=json.loads(owner._raw)
        role=json.loads(self._declaration)['request']['role']
        if role!='actual' or receipt.role!='reference':raise ValueError('Actual requires reference parent completion')
        expected=dict(root=receipt.scientific_root,terminal_sha256=receipt.scientific_terminal_sha256,
            request_sha256=receipt.scientific_request_sha256,max_archive_bytes=receipt.max_archive_bytes)
        _same(declaration['declaration']['reference'],expected)
        for field in ('hour','manifest','source_binding','run_configuration','provenance'):
            _same(declaration['declaration'][field],other['declaration'][field])
        for field in ('phase_request','state','source_audit','source_observation','exogenous'):
            _same(declaration['projection'][field],other['projection'][field])
        return dict(root=str(owner.root),parent_terminal_sha256=receipt.terminal_sha256,
            completion_sha256=io.digest(_completion_bytes(receipt)))

    def _reference_initial(self):
        role=json.loads(self._declaration)['request']['role']
        owner,receipt=self._reference_owner,self._reference_completion
        if role=='reference':
            if owner is not None or receipt is not None:raise ValueError('Rref cannot take a reference completion')
            return None
        if type(owner) is not Parent or type(receipt) is not ParentCompletion:
            raise TypeError('exact live same-module reference parent and completion required')
        owner.validate_completion(receipt)
        return self._reference_match(owner,receipt)

    def _reference(self):
        if self._reference_owner is None:return
        if not self._reference_held:raise ValueError('reference operation lease required')
        self._reference_owner._validate(self._reference_completion)
        _same(self._reference_match(self._reference_owner,self._reference_completion),self._reference_descriptor)

    def _enter(self):
        if not self._guard.acquire(blocking=False):raise ValueError('selector parent operation already active')
        try:self._check()
        except BaseException:self._guard.release();raise

    def _inspect(self,child,output_pins=None):
        declaration=json.loads(self._declaration);launch=json.loads(self._launch)
        pins={name:io.digest(self._records['worker_non_authoritative/'+name][1]) for name in inspection.INPUT_FILES}
        return inspection.inspect(self.worker_root,pins=pins,environment=declaration['environment'],
            expected_process_identity=launch['process_identity'],expected_pid=child['pid'],
            expected_creation_filetime=child['creation_filetime'],expected_output_pins=output_pins)

    def run(self):
        """Real Job/native call path. No run authorization is inferred here."""
        scope=_CHECK;scope();owner_check=Parent._check
        self._enter();reference=self._reference_owner;attempted=False
        try:
            if self._state!='prepared':raise ValueError('selector parent is single-attempt')
            self._state='running';attempted=True
            if reference is not None:
                reference._enter();self._reference_held=True
            self._source();self._reference()
            worker._roots(self.worker_root,{'request.json','selector_snapshot.json','launch.json','scratch_non_authoritative'})
            declaration=json.loads(self._declaration);launch=json.loads(self._launch)
            host_value=launch['host']
            host=process.resources.HostResourceBudget(host_value['additional_commit_bytes'],host_value['commit_reserve_bytes'],
                tuple(process.resources.DirectoryDemand(**item) for item in host_value['directories']))
            budget=process.TaskProcessBudget(**launch['budget'])
            called=[];child_saved=None;observed_saved=None;inspection_saved=None
            run_job=lifecycle.run_job;read_outputs=self._inspect
            def check():scope();owner_check(self)
            def before_release(child,initial):
                nonlocal child_saved
                check()
                if called:raise ValueError('single suspended release callback required')
                called.append('release')
                if set(child)!={'pid','creation_filetime','process_identity'} or child['process_identity']!=launch['process_identity']:
                    raise ValueError('selector child identity differs')
                lifecycle._integer(child['pid'],True);lifecycle._integer(child['creation_filetime'],True)
                worker._validate_initial(initial,host)
                child_saved=io.encode(child)
                raw=io.encode(initial);self._keep('worker_non_authoritative/initial_observation.json',raw,worker.CAP)
                child_raw=io.encode(dict(child,request_sha256=launch['request_sha256'],initial_observation_sha256=io.digest(raw)))
                self._keep('worker_non_authoritative/child.json',child_raw,worker.CAP)
                release=io.encode(dict(request_sha256=launch['request_sha256'],launch_sha256=io.digest(self._launch),child_sha256=io.digest(child_raw)))
                self._keep('worker_non_authoritative/release_intent.json',release,worker.CAP)
                worker._roots(self.worker_root,worker.INPUTS)
                self._source();self._reference();check()
            def on_quiescent(observed):
                nonlocal observed_saved,inspection_saved
                check()
                if called!=['release']:raise ValueError('single post-release quiescence callback required')
                called.append('quiescent');child=json.loads(child_saved)
                for key,value in child.items():
                    if observed.get(key)!=value:raise ValueError('live Job observation child differs')
                observed_saved=io.encode(observed)
                diagnostic=read_outputs(child)
                inspection_saved=io.encode(diagnostic)
                self._source();self._reference();check()
                return diagnostic
            outcome=run_job(launch['argv'],cwd=Path(launch['cwd']),environment=declaration['environment'],
                budget=budget,host_budget=host,expected_process_identity=launch['process_identity'],
                before_release=before_release,on_quiescent=on_quiescent)
            check()
            if called!=['release','quiescent']:raise ValueError('complete owned callback order required')
            child=json.loads(child_saved)
            expected=dict(schema=lifecycle.SCHEMA,implementation=lifecycle.implementation_identity(),
                **child,observation=json.loads(observed_saved),inspection=json.loads(inspection_saved),
                clock=worker.sequence.timed.capture.clock_profile(),diagnostic_window=outcome.get('diagnostic_window'),**lifecycle.FLAGS)
            _same(outcome,expected)
            window=outcome['diagnostic_window'];keys=('start_ns','release_ns','quiescent_ns','end_ns')
            if set(window)!=set(keys) or any(type(window[k]) is not int or window[k]<0 for k in keys) or list(window[k] for k in keys)!=sorted(window.values()):
                raise ValueError('parent diagnostic clock differs')
            self._source();self._reference()
            self._outcome=io.encode(outcome)
            terminal=io.encode(dict(schema=SCHEMA,implementation=self._own,binding_sha256=io.digest(self._binding),
                request_keys=self._request_keys(),
                reference_execution=self._reference_descriptor,lifecycle=outcome,**FLAGS))
            self._keep('terminal.json',terminal,TERMINAL_CAP)
            self._state='complete'
            self._retained()
            data=outcome['inspection']['data'];request=declaration['request']
            receipt=ParentCompletion((str(self.root),request['role'],io.digest(terminal),
                str(self.worker_root/'science_sequence_non_authoritative'),data['scientific_terminal_sha256'],
                self._request_keys()['scientific_request_sha256'],data['sequence_request_sha256'],request['max_archive_bytes']),_token=_TOKEN)
            self._issued=receipt;self._issued_bytes=_completion_bytes(receipt)
            check();return receipt
        except BaseException:
            if attempted:self._state='failed';self._issued=None;self._issued_bytes=None
            raise
        finally:
            if self._reference_held:self._reference_held=False;reference._guard.release()
            self._guard.release()

    def _request_keys(self):
        request=json.loads(self._declaration)['request']
        return dict(scientific_request_sha256=io.digest(io.encode(request['sequence_configuration']['scientific_configuration'])),
            sequence_request_sha256=request['sequence_request_sha256'])

    def _retained(self):
        self._check();self._source();self._reference()
        if self._outcome is None:raise ValueError('completed owned outcome required')
        outcome=json.loads(self._outcome);prior=outcome['inspection'];data=prior['data']
        fresh=self._inspect(dict(pid=outcome['pid'],creation_filetime=outcome['creation_filetime']),
            {name:data['pins'][name] for name in inspection.OUTPUT_FILES})
        expected=deepcopy(prior);expected['data']['output_pins_externally_supplied']=True
        _same(fresh,expected)
        terminal=io.encode(dict(schema=SCHEMA,implementation=self._own,binding_sha256=io.digest(self._binding),
            request_keys=self._request_keys(),
            reference_execution=self._reference_descriptor,lifecycle=outcome,**FLAGS))
        if self._records['terminal.json'][1]!=terminal:raise ValueError('parent outcome terminal changed')
        self._reference();self._check()

    def _validate(self,receipt):
        self._check()
        if self._state!='complete' or receipt is not self._issued or _completion_bytes(receipt)!=self._issued_bytes:
            raise ValueError('exact original issued parent completion required')
        self._retained()
        if any(getattr(receipt,key)!=value for key,value in self._request_keys().items()):
            raise ValueError('completion request keys differ')
        if receipt.terminal_sha256!=io.digest(self._records['terminal.json'][1]):raise ValueError('completion terminal differs')

    def validate_completion(self,receipt):
        scope=_CHECK;scope();self._enter();reference=self._reference_owner
        try:
            if reference is not None:reference._enter();self._reference_held=True
            self._validate(receipt);scope()
        finally:
            if self._reference_held:self._reference_held=False;reference._guard.release()
            self._guard.release()

    def close(self):return _CLEANUP(self)

    def __enter__(self):self._check();return self
    def __exit__(self,*args):self.close()
    def __copy__(self):raise TypeError('parent cannot be copied')
    def __deepcopy__(self,memo):raise TypeError('parent cannot be copied')
    def __reduce_ex__(self,protocol):raise TypeError('parent cannot be serialized')


def _dependency_scope():
    return io.encode([lifecycle.SCHEMA,dict(lifecycle.FLAGS),lifecycle.INSPECTION_SCHEMA,lifecycle.INSPECTION_CAP,
        inspection.SCHEMA,dict(inspection.FLAGS),sorted(inspection.FILES),sorted(inspection.INPUT_FILES),
        sorted(inspection.OUTPUT_FILES),preparation.PARENT_BYTES])


_DEPENDENCY_SCOPE=_dependency_scope()
def _anchor_check():
    namespace=vars(sys.modules[__name__])
    verify,owner_type=_verify,Parent
    registry,registry_lock=_OWNERS,_REGISTRY_LOCK
    pid,thread,lease_close=os.getpid,get_ident,local._Lease.close
    def cleanup(self):
        if type(self) is not owner_type:raise TypeError('exact parent required for cleanup')
        if not self._guard.acquire(blocking=False):raise ValueError('cannot close active selector parent')
        try:
            if (self._pid,self._thread)!=(pid(),thread()):raise ValueError('creating owner required for close')
            if self._state=='closed':return
            try:
                if self._lease is not None:lease_close(self._lease)
            finally:
                self._state='closed'
                with registry_lock:
                    if registry.get(self._nonce) is self:registry.pop(self._nonce)
        finally:self._guard.release()
    def leave(self,*args):return cleanup(self)
    namespace['_CLEANUP']=cleanup
    owner_type.close,owner_type.__exit__=cleanup,leave
    def check():
        if namespace.get('_CHECK') is not check or any(namespace.get(name) is not value for name,value in retained):
            raise ValueError('selector parent original scope changed')
        verify()
    def guarded(function):
        def entry(*args,**kwargs):
            if not args or type(args[0]) is not owner_type:raise TypeError('exact original selector parent required')
            check()
            return function(*args,**kwargs)
        return entry
    # Entry wrappers retain the original checker even if its global name was
    # replaced before a call. close remains available for failure cleanup.
    for name in ('__init__','run','validate_completion','__enter__','_check'):
        setattr(Parent,name,guarded(vars(Parent)[name]))
    namespace['_FIXED']=tuple((owner,name,vars(owner)[name]) for owner,name,_ in _FIXED)
    retained=tuple((name,value) for name,value in namespace.items() if name!='_CHECK')
    return check


_IDENTITY=implementation_identity
_FIXED=tuple((owner,name,value) for owner in (sys.modules[__name__],Parent,ParentCompletion)
    for name,value in tuple(vars(owner).items()) if isinstance(value,(FunctionType,property,staticmethod,classmethod)))+tuple(
    (owner,name,vars(owner)[name]) for owner,names in (
        (sys.modules[__name__],('_IDENTITY','preparation','lifecycle','inspection','worker','io','process','local',
            '_TOKEN','_OWNERS','_REGISTRY_LOCK','_COMPLETION_FIELDS','_DEPENDENCY_SCOPE')),
        (preparation,('prepare','bind','implementation_identity','_CHECK')),
        (lifecycle,('run_job','implementation_identity','_integer')),
        (inspection,('inspect','implementation_identity')),
        (local,('_Lease',)),(local._Lease,('check','close')),
        (io,('write_new','encode','digest')),
        (worker,('_read','_roots','_validate_initial')),
        (json,('loads','dumps')),(os,('getpid',)),(Path,('read_bytes','mkdir')),
    ) for name in names)+tuple((preparation,name,value) for name,value in vars(preparation).items() if not name.startswith('__'))
_CHECK=_anchor_check()
