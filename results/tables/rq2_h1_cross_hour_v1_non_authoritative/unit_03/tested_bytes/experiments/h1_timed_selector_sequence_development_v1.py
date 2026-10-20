"""Complete timed selector chain, development only; no CLI or Job authority.

Science archives retain the closed legacy wire contract. External timing commits
identify this producer. Real use requires fresh native authority and owned Job
supervision; tests use fabricated adapters.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat
from threading import Lock, get_ident
from types import MappingProxyType
from uuid import uuid4

from experiments import h1_owned_selector_sequence_development_v1 as legacy
from experiments import h1_selector_timed_stage_development_v1 as timed

io,selection=legacy.io,legacy.selection
SCHEMA='h1_timed_selector_sequence_development_v1'
META_CAP=legacy.META_CAP
ROOT_ID_MAX=2**256-1
FLAGS=MappingProxyType(dict(legacy.FLAGS,legacy_producer_execution_authenticated=False,
    old_owned_return_observed=False,live_timing_authenticated=False,non_solver_allowance_verified=False))
_TOKEN=object()


def implementation_identity():
    if SCHEMA!='h1_timed_selector_sequence_development_v1' or any(v is not False for v in FLAGS.values()):
        raise ValueError('timed selector scope changed')
    return io.digest(io.encode([SCHEMA,io.digest(Path(__file__).read_bytes()),
        legacy.implementation_identity(),timed.implementation_identity()]))


def _configuration(context,args,archive_bytes,timing_bytes,config):
    science=legacy._configuration(*context,args,archive_bytes,config)
    required=2*META_CAP+len(science['labels'])*(META_CAP+2*timed.capture.CAP+4*io.META_CAP)
    if type(timing_bytes) is not int or not required<=timing_bytes<=2**63-1:
        raise ValueError('complete timing archive envelope exceeds byte bound')
    return dict(scientific_configuration=science,max_timing_archive_bytes=timing_bytes,
        required_timing_archive_bytes=required,implementation=implementation_identity(),
        timed_stage_implementation=timed.implementation_identity())


def _roots(root,side):
    root=legacy._root(root);side=legacy._root(side)
    if root==side or root in side.parents or side in root.parents:
        raise ValueError('external nonnested sequence timing root required')
    return root,side


def _read(path,cap=META_CAP):
    s=path.stat(follow_symlinks=False)
    if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or getattr(s,'st_file_attributes',0)&1024:
        raise ValueError('plain single-link sequence evidence required')
    return io.read_stable(path,cap)


def _doc(raw):
    value=json.loads(raw)
    if type(value) is not dict or io.encode(value)!=raw:raise ValueError('canonical sequence object required')
    return value


def _header(root,side,configuration,science_pin,nonce,pid,thread,start,directory_identity):
    for value in (pid,thread):
        if timed.capture.timing.integer(value)==0:raise ValueError('positive sequence owner required')
    timed.capture.timing.integer(start)
    if (type(directory_identity) is not tuple or len(directory_identity)!=2
            or any(type(v) is not int or not 0<=v<=ROOT_ID_MAX for v in directory_identity)):
        raise ValueError('bounded exact directory identity required')
    # The legacy header constructor checks the exact nonce separately.
    return dict(schema=SCHEMA,configuration=configuration,scientific_root=str(root),timing_root=str(side),
        scientific_directory_identity=directory_identity,scientific_binding_sha256=science_pin,
        nonce=nonce,pid=pid,thread_id=thread,sequence_start_ns=start,clock=timed.capture.clock_profile(),**FLAGS)


def _snapshot(root,side,count,limits,science_terminal=False,timing_terminal=False,pending=False):
    science=legacy._snapshot(root,count,limits,science_terminal,pending)
    spaces={side:{'binding.json','stages','commits'}|({'terminal.json'} if timing_terminal else set()),
        side/'stages':{f'{i:04d}' for i in range(count+int(pending))},
        side/'commits':{f'{i:04d}.json' for i in range(count)}}
    dirs={str(p.relative_to(side)):legacy.stage._directory(p,n) for p,n in spaces.items()}
    files={'binding.json':_read(side/'binding.json')}
    if timing_terminal:files['terminal.json']=_read(side/'terminal.json')
    for i in range(count):files[f'commits/{i:04d}.json']=_read(side/'commits'/f'{i:04d}.json')
    children=tuple(timed._view(root/'stages'/f'{i:04d}',side/'stages'/f'{i:04d}',limits)
        for i in range(count+int(pending)))
    return science,(dirs,files,children)


def _extends(before,after):
    # Only the three parent directory timestamps may change as the next stage
    # appears; prior file stamps and all completed child namespaces are retained.
    for old,new in ((before[0],after[0]),(before[1],after[1])):
        if any(new[1].get(k)!=v for k,v in old[1].items()):return False
        if any(new[0][k][:2]!=v[:2] or (k not in ('.','stages','commits') and new[0][k]!=v)
                for k,v in old[0].items()):return False
    return after[1][2][:len(before[1][2])]==before[1][2]


def _snapshot_pin(view,root,side):
    """Bind mutable view containers through a canonical immutable projection."""
    science,(dirs,files,children)=view
    def relative(path):
        for label,base in (('science',root),('timing',side)):
            if path==base or base in path.parents:return label,path.relative_to(base).as_posix()
        raise ValueError('view path outside sequence roots')
    child_views=[]
    for child_dirs,child_files in children:
        child_views.append((sorted((relative(p),v) for p,v in child_dirs.items()),
            sorted((relative(p),cap,io.digest(raw),stamp) for p,(cap,(raw,stamp)) in child_files.items())))
    return io.digest(io.encode((sorted(science[0].items()),sorted(science[1].items()),
        sorted(dirs.items()),sorted((name,META_CAP,io.digest(raw),stamp) for name,(raw,stamp) in files.items()),child_views)))


def _commit(key,head,index,label,science_pin,result,side,view):
    binding=_doc(view[1][side/'binding.json'][1][0])
    stage_end=_doc(view[1][side/'terminal.json'][1][0])
    native=_doc(view[1][side/'native/completion.json'][1][0])
    return dict(schema=SCHEMA,request_sha256=key,previous_sha256=head,index=index,label=label,
        scientific_commit_sha256=science_pin,stage_request_sha256=result['science']['request_key'],
        stage_terminal_sha256=result['science']['terminal_sha256'],
        timing_binding_sha256=result['sidecar_binding_sha256'],timing_terminal_sha256=result['sidecar_terminal_sha256'],
        pid=binding['pid'],thread_id=binding['thread_id'],clock=binding['clock'],
        stage_start_ns=stage_end['stage_start_ns'],stage_end_ns=stage_end['stage_end_ns'],
        native_start_ns=native['native_start_ns'],native_end_ns=native['native_end_ns'],
        native_interval_ns=result['native_interval_ns'],apply_window_ns=result['apply_window_ns'],**FLAGS)


def _prefix(root,side,context,args,archive_bytes,timing_bytes,config,count,science_terminal=False,timing_terminal=False):
    configuration=_configuration(context,args,archive_bytes,timing_bytes,config)
    labels=configuration['scientific_configuration']['labels']
    if type(count) is not int or not 0<=count<=len(labels):raise ValueError('bounded complete prefix required')
    view=_snapshot(root,side,count,args['limits'],science_terminal,timing_terminal)
    raw=view[1][1]['binding.json'][0];header=_doc(raw)
    needed={'schema','configuration','scientific_root','timing_root','scientific_directory_identity',
        'scientific_binding_sha256','nonce','pid','thread_id','sequence_start_ns','clock'}|set(FLAGS)
    if set(header)!=needed:raise ValueError('timed sequence header fields differ')
    science_raw=_read(root/'binding.json')[0]
    if science_raw!=legacy._header(root,configuration['scientific_configuration'],header['nonce']):
        raise ValueError('legacy scientific header differs')
    expected=_header(root,side,configuration,io.digest(science_raw),header['nonce'],
        header['pid'],header['thread_id'],header['sequence_start_ns'],timed.capture.directory(root))
    if raw!=io.encode(expected):raise ValueError('timed sequence header differs')
    science=legacy._replay(root,*context,args,archive_bytes,config,count=count,terminal=science_terminal,
        binding_pin=header['scientific_binding_sha256'])
    key=io.digest(io.encode(configuration));head=io.digest(raw);records=();vector=[];end=header['sequence_start_ns']
    for i in range(count):
        path=side/'stages'/f'{i:04d}'
        saved=view[1][1][f'commits/{i:04d}.json'][0];doc=_doc(saved)
        pin=doc.get('timing_terminal_sha256');io.pin(pin)
        result=timed.inspect(root/'stages'/f'{i:04d}',path,*context,records,
            expected_terminal_sha256=pin,**args)
        science_commit=io.digest(_read(root/'commits'/f'{i:04d}.json')[0])
        expected=_commit(key,head,i,labels[i],science_commit,result,path,view[1][2][i])
        if saved!=io.encode(expected):raise ValueError('timing commit differs from joint replay')
        if (expected['pid']!=header['pid'] or expected['thread_id']!=header['thread_id']
                or expected['clock']!=header['clock'] or expected['stage_start_ns']<end):
            raise ValueError('timed stage owner or chronological ordering differs')
        end=expected['stage_end_ns'];vector.append(expected);head=io.digest(saved)
        records+=(result['science']['selector_record'],)
    if records!=science['records']:raise ValueError('timed and scientific record vectors differ')
    if (_snapshot(root,side,count,args['limits'],science_terminal,timing_terminal)!=view
            or _configuration(context,args,archive_bytes,timing_bytes,config)!=configuration):
        raise ValueError('timed sequence changed during replay')
    return dict(configuration=configuration,key=key,binding=io.digest(raw),head=head,header=header,
        records=records,vector=tuple(vector),science=science,view=view,last_end_ns=end)


def _terminal(prefix,science_pin,end):
    timed.capture.timing.integer(end)
    if end<prefix['last_end_ns']:raise ValueError('sequence window excludes final stage')
    total=timed.capture.timing.integer(sum(v['native_interval_ns'] for v in prefix['vector']))
    return dict(schema=SCHEMA,request_sha256=prefix['key'],binding_sha256=prefix['binding'],
        last_commit_sha256=prefix['head'],scientific_terminal_sha256=science_pin,
        scientific_last_commit_sha256=prefix['science']['head'],
        stage_count=len(prefix['vector']),stage_timing_terminal_sha256=tuple(v['timing_terminal_sha256'] for v in prefix['vector']),
        native_interval_ns=total,stage_vector=prefix['vector'],
        window_scope='constructor_to_preterminal_ownership_diagnostic',
        sequence_start_ns=prefix['header']['sequence_start_ns'],sequence_end_ns=end,**FLAGS)


def inspect(root,timing_root,frame,disclosure,before,*,expected_terminal_sha256,
            max_archive_bytes,max_timing_archive_bytes,run_configuration,**args):
    """Conditional saved replay; cannot authenticate elapsed time or execution."""
    with legacy.bridge.science.prior.guard.solver_calls_forbidden():
        root,side=_roots(root,timing_root);context=(frame,disclosure,before)
        io.pin(expected_terminal_sha256)
        raw=_read(side/'terminal.json');terminal=_doc(raw[0])
        if io.digest(raw[0])!=expected_terminal_sha256:raise ValueError('external timing sequence terminal differs')
        science_pin=terminal.get('scientific_terminal_sha256');io.pin(science_pin)
        if io.digest(_read(root/'terminal.json')[0])!=science_pin:raise ValueError('retained scientific sequence pin differs')
        count=len(selection.stage_labels(frame,args['lane']))
        view=_snapshot(root,side,count,args['limits'],True,True)
        prefix=_complete_prefix(root,side,context,args,max_archive_bytes,max_timing_archive_bytes,run_configuration)
        if raw[0]!=io.encode(_terminal(prefix,science_pin,terminal.get('sequence_end_ns'))):
            raise ValueError('timed sequence terminal reconstruction differs')
        checked=legacy.inspect(root,*context,expected_terminal_sha256=science_pin,
            max_archive_bytes=max_archive_bytes,run_configuration=run_configuration,**args)
        if _snapshot(root,side,count,args['limits'],True,True)!=view or _read(side/'terminal.json')!=raw:
            raise ValueError('complete timed sequence view changed')
        return dict(science=checked,records=prefix['records'],request_sha256=prefix['key'],
            terminal_sha256=expected_terminal_sha256,scientific_terminal_sha256=science_pin,
            native_interval_ns=terminal['native_interval_ns'],stage_vector=prefix['vector'],
            sequence_window_ns=terminal['sequence_end_ns']-terminal['sequence_start_ns'],fresh_at_return=True,**FLAGS)


def _complete_prefix(root,side,context,args,archive_bytes,timing_bytes,config):
    return _prefix(root,side,context,args,archive_bytes,timing_bytes,config,
        len(selection.stage_labels(context[0],args['lane'])),True,True)


@dataclass(frozen=True,init=False)
class TimedSequenceCompletion:
    root: str
    timing_root: str
    terminal_sha256: str
    scientific_terminal_sha256: str
    request_sha256: str
    records: tuple
    archive_view_sha256: str
    authority_flags: tuple

    def __init__(self,root,side,result,*,archive_view_sha256=None,_token=None):
        if _token is not _TOKEN:raise TypeError('live timed sequence completion required')
        io.pin(archive_view_sha256)
        values=(str(root),str(side),result['terminal_sha256'],result['scientific_terminal_sha256'],
            result['request_sha256'],result['records'],archive_view_sha256,tuple(FLAGS.items()))
        for name,value in zip(self.__annotations__,values):object.__setattr__(self,name,value)


class OwnedTimedSelectorSequence:
    def __init__(self,root,timing_root,frame,disclosure,before,*,max_archive_bytes,
                 max_timing_archive_bytes,run_configuration,**args):
        self.root,self.side=_roots(root,timing_root)
        if self.root.exists() or self.side.exists():raise FileExistsError('fresh science and timing sequence roots required')
        self.context=(frame,disclosure,before);self.args=dict(args)
        self.archive_bytes=max_archive_bytes;self.timing_bytes=max_timing_archive_bytes;self.run_configuration=run_configuration
        self._runner=self._original_runner=timed._run_stage;self._reader=self._original_reader=timed.inspect
        self._legacy_readers=(legacy._replay,legacy.inspect)
        configuration=self._config();self._configuration=io.encode(configuration);self.key=io.digest(self._configuration)
        self._implementation=implementation_identity();self.count=len(configuration['scientific_configuration']['labels'])
        self._pid,self._thread=os.getpid(),get_ident();self._self=self
        self._operation=self._original_operation=Lock();self._nonce=self._issued_nonce=None
        self._receipt=self._receipt_bytes=self._final_view=None
        self.started=self.complete=self.poisoned=False
        start=timed.capture.timing.integer(timed.capture._CLOCK());timed.capture.clock_profile()
        nonce=uuid4().hex
        self._science_header=legacy._header(self.root,configuration['scientific_configuration'],nonce)
        if len(self._science_header)>META_CAP:raise ValueError('science header cap exceeded')
        maximum_header=_header(self.root,self.side,configuration,io.digest(self._science_header),
            nonce,self._pid,self._thread,start,(ROOT_ID_MAX,ROOT_ID_MAX))
        if len(io.encode(maximum_header))>META_CAP:raise ValueError('timing header cap exceeded before mkdir')
        for path in (self.root,self.side):
            path.mkdir(exist_ok=False);(path/'stages').mkdir();(path/'commits').mkdir()
        io.write_new(self.root/'binding.json',self._science_header)
        self._header=io.encode(_header(self.root,self.side,configuration,io.digest(self._science_header),
            nonce,self._pid,self._thread,start,timed.capture.directory(self.root)))
        if len(self._header)>META_CAP:raise ValueError('timing header cap exceeded')
        io.write_new(self.side/'binding.json',self._header)
        self._initial_view=self._view(0)
        self._initial_view_pin=_snapshot_pin(self._initial_view,self.root,self.side)
        self._fixed=(self.root,self.side,self.archive_bytes,self.timing_bytes,self.count,self.key,self._science_header,self._header,self._configuration,self._initial_view_pin)

    def _config(self):return _configuration(self.context,self.args,self.archive_bytes,self.timing_bytes,self.run_configuration)

    def _view(self,count,science_terminal=False,timing_terminal=False,pending=False):
        return _snapshot(self.root,self.side,count,self.args['limits'],science_terminal,timing_terminal,pending)

    def _check(self):
        if (self._self is not self or (os.getpid(),get_ident())!=(self._pid,self._thread) or self.poisoned
                or self._operation is not self._original_operation or not self._original_operation.locked()
                or self._runner is not self._original_runner or self._reader is not self._original_reader
                or timed._run_stage is not self._runner or timed.inspect is not self._reader
                or (legacy._replay,legacy.inspect)!=self._legacy_readers
                or implementation_identity()!=self._implementation or io.encode(self._config())!=self._configuration
                or (self.root,self.side,self.archive_bytes,self.timing_bytes,self.count,self.key,self._science_header,self._header,self._configuration,self._initial_view_pin)!=self._fixed
                or _snapshot_pin(self._initial_view,self.root,self.side)!=self._initial_view_pin
                or _read(self.root/'binding.json')!=(self._science_header,self._initial_view[0][1]['binding.json'][1])
                or _read(self.side/'binding.json')!=self._initial_view[1][1]['binding.json']):
            raise ValueError('timed sequence live identity or configuration changed')
        for root,view in ((self.root,self._initial_view[0]),(self.side,self._initial_view[1])):
            for name in ('.','stages','commits'):
                if timed.capture.directory(root/name)!=view[0][name][:2]:raise ValueError('sequence directory identity changed')

    def _prefix(self,count,science_terminal=False):
        return _prefix(self.root,self.side,self.context,self.args,self.archive_bytes,self.timing_bytes,
            self.run_configuration,count,science_terminal)

    def run(self):
        if self._operation is not self._original_operation:raise ValueError('timed sequence guard changed')
        if not self._original_operation.acquire(False):raise ValueError('timed sequence active')
        try:
            self._check()
            if self.started or self.complete or self._nonce is not None:raise ValueError('timed sequence consumed')
            self.started=True;nonce=self._nonce=object();records=();head=io.digest(self._header)
            retained_view=self._initial_view
            for i in range(self.count):
                self._check()
                if self._nonce is not nonce or self._view(i)!=retained_view:
                    raise ValueError('retained timed archive changed before replay')
                with legacy.bridge.science.prior.guard.solver_calls_forbidden():prefix=self._prefix(i)
                if prefix['records']!=records or prefix['head']!=head:raise ValueError('retained timed prefix differs')
                path=self.root/'stages'/f'{i:04d}';side=self.side/'stages'/f'{i:04d}'
                key=legacy.bridge.request_key(*self.context,records,**self.args)
                if self._view(i)!=prefix['view']:raise ValueError('timed prefix changed before release')
                self._check()
                if self._nonce is not nonce:raise ValueError('timed sequence nonce changed')
                returned=self._runner(path,side,*self.context,records,expected_key=key,**self.args)
                self._check()
                if self._nonce is not nonce:raise ValueError('timed sequence nonce changed')
                with legacy.bridge.science.prior.guard.solver_calls_forbidden():
                    if type(returned) is not dict:raise ValueError('typed timed stage return required')
                    stage_view=timed._view(path,side,self.args['limits'])
                    checked=self._reader(path,side,*self.context,records,
                        expected_terminal_sha256=returned.get('sidecar_terminal_sha256'),**self.args)
                    if returned!=checked or checked['science']['request_key']!=key or checked['science']['selector_chain_complete'] is not (i==self.count-1):
                        raise ValueError('timed stage return differs from fresh inspection')
                    self._check()
                    if (self._nonce is not nonce or not _extends(prefix['view'],self._view(i,pending=True))
                            or timed._view(path,side,self.args['limits'])!=stage_view):
                        raise ValueError('prior timed evidence changed during stage')
                    label=selection.stage_labels(self.context[0],self.args['lane'])[i]
                    scientific=legacy._commit(prefix['science']['key'],prefix['science']['head'],i,label,checked['science'],records)
                    science_pin=legacy._write(self.root/'commits'/f'{i:04d}.json',scientific)
                    if _read(self.root/'commits'/f'{i:04d}.json')[0]!=io.encode(scientific):
                        raise ValueError('scientific commit readback differs')
                    commit=_commit(self.key,head,i,label,science_pin,checked,side,stage_view)
                    if (commit['pid']!=self._pid or commit['thread_id']!=self._thread or commit['clock']!=prefix['header']['clock']
                            or commit['stage_start_ns']<prefix['last_end_ns']):raise ValueError('timed stage owner or chronology differs')
                    head=legacy._write(self.side/'commits'/f'{i:04d}.json',commit)
                    if _read(self.side/'commits'/f'{i:04d}.json')[0]!=io.encode(commit):
                        raise ValueError('timing commit readback differs')
                    records+=(checked['science']['selector_record'],)
                    retained_view=self._view(i+1)
                    if (not _extends(prefix['view'],retained_view)
                            or timed._view(path,side,self.args['limits'])!=stage_view):
                        raise ValueError('timed archive changed during paired commit')
            with legacy.bridge.science.prior.guard.solver_calls_forbidden():
                if self._view(self.count)!=retained_view:raise ValueError('final retained timed archive changed')
                fresh=self._prefix(self.count)
                if fresh['records']!=records or fresh['head']!=head:raise ValueError('final timed prefix differs')
                self._check()
                if self._nonce is not nonce:raise ValueError('final timed sequence nonce changed')
                scientific=fresh['science']
                science_pin=legacy._write(self.root/'terminal.json',legacy._terminal(scientific['key'],scientific['binding'],scientific['head'],scientific['replay']))
                legacy.inspect(self.root,*self.context,expected_terminal_sha256=science_pin,
                    max_archive_bytes=self.archive_bytes,run_configuration=self.run_configuration,**self.args)
                fresh=self._prefix(self.count,True);self._check()
                if self._nonce is not nonce:raise ValueError('final timed sequence nonce changed')
                pin=legacy._write(self.side/'terminal.json',_terminal(fresh,science_pin,timed.capture._CLOCK()))
                result=self._inspect(pin);self._check()
                if self._nonce is not nonce:raise ValueError('completion nonce changed')
                self._final_view=self._view(self.count,True,True)
                self._receipt=TimedSequenceCompletion(self.root,self.side,result,
                    archive_view_sha256=_snapshot_pin(self._final_view,self.root,self.side),_token=_TOKEN)
                self._receipt_bytes=self._receipt_snapshot(self._receipt);self._issued_nonce=nonce
                self.complete=True
                return self._receipt
        except BaseException:self.poisoned=True;raise
        finally:self._original_operation.release()

    def _inspect(self,pin):
        return inspect(self.root,self.side,*self.context,expected_terminal_sha256=pin,max_archive_bytes=self.archive_bytes,
            max_timing_archive_bytes=self.timing_bytes,run_configuration=self.run_configuration,**self.args)

    def validate_completion(self,receipt):
        if not self._original_operation.acquire(False):raise ValueError('timed sequence active')
        try:
            self._check()
            if (not self.complete or not self.started or self._nonce is None or self._nonce is not self._issued_nonce
                    or type(receipt) is not TimedSequenceCompletion or receipt is not self._receipt
                    or self._receipt_snapshot(receipt)!=self._receipt_bytes
                    or _snapshot_pin(self._final_view,self.root,self.side)!=receipt.archive_view_sha256
                    or _snapshot_pin(self._view(self.count,True,True),self.root,self.side)!=receipt.archive_view_sha256):
                raise ValueError('exact live timed sequence completion required')
            result=self._inspect(receipt.terminal_sha256);self._check()
            if (result['records']!=receipt.records or self._receipt_snapshot(receipt)!=self._receipt_bytes
                    or self._nonce is not self._issued_nonce
                    or _snapshot_pin(self._final_view,self.root,self.side)!=receipt.archive_view_sha256
                    or _snapshot_pin(self._view(self.count,True,True),self.root,self.side)!=receipt.archive_view_sha256):
                raise ValueError('timed completion changed')
            return result
        except BaseException:self.poisoned=True;raise
        finally:self._original_operation.release()

    @staticmethod
    def _receipt_snapshot(receipt):
        return io.encode([receipt.root,receipt.timing_root,receipt.terminal_sha256,receipt.scientific_terminal_sha256,
            receipt.request_sha256,[io.digest(r) for r in receipt.records],receipt.archive_view_sha256,receipt.authority_flags])

    def _no_copy(self,*args):raise TypeError('live timed sequence cannot be copied')
    __copy__=__deepcopy__=__reduce_ex__=_no_copy
