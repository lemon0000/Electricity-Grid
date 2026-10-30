"""Prepared Win32 resource effects for the outer host. All issuers remain closed.

Ordinary tests substitute only the DLL, clock and memory observation leaves in
a private copy. No factory here grants source-root or Native run authority.
"""
import ctypes as C
from ctypes import wintypes as W
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from threading import get_ident,current_thread

ROOT=Path(__file__).absolute().parents[1]
EXE=str(Path('D:/Miniconda3/envs/compute/python.exe'))
SIZE_T=C.c_size_t
HANDLE=W.HANDLE
DWORD=W.DWORD
NAMES=('mapping','mutex','view','job','thread','process')
MAP_BYTES=69632
STOP_CENSUS_SECONDS=0.5
SOURCE_EPOCH='acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'


class _Basic(C.Structure):
    _fields_=[('process_time',C.c_longlong),('job_time',C.c_longlong),('flags',DWORD),
        ('min_ws',SIZE_T),('max_ws',SIZE_T),('active_processes',DWORD),('affinity',SIZE_T),('priority',DWORD),('scheduling',DWORD)]


class _IO(C.Structure):
    _fields_=[(name,C.c_ulonglong) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]


class _Limits(C.Structure):
    _fields_=[('basic',_Basic),('io',_IO),('process_memory',SIZE_T),('job_memory',SIZE_T),('peak_process',SIZE_T),('peak_job',SIZE_T)]


class _Startup(C.Structure):
    _fields_=[('cb',DWORD),('reserved',W.LPWSTR),('desktop',W.LPWSTR),('title',W.LPWSTR)]+[(name,DWORD) for name in
        ('x','y','x_size','y_size','x_chars','y_chars','fill','flags')]+[('show',W.WORD),('reserved_size',W.WORD),
        ('reserved_ptr',C.c_void_p),('stdin',HANDLE),('stdout',HANDLE),('stderr',HANDLE)]


class _StartupEx(C.Structure):
    _fields_=[('startup',_Startup),('attributes',C.c_void_p)]


class _ProcessInfo(C.Structure):
    _fields_=[('process',HANDLE),('thread',HANDLE),('pid',DWORD),('tid',DWORD)]


class _Accounting(C.Structure):
    _fields_=[(name,C.c_longlong) for name in ('user','kernel','period_user','period_kernel')]+[
        (name,DWORD) for name in ('faults','total','active','terminated')]


class _MemoryInfo(C.Structure):
    _fields_=[('base',C.c_void_p),('allocation',C.c_void_p),('allocation_protect',DWORD),('partition',W.WORD),
        ('region_size',SIZE_T),('state',DWORD),('protect',DWORD),('kind',DWORD)]


class NativeUnavailable(RuntimeError):pass


class ProviderUnresolved(RuntimeError):
    def __init__(self,provider,primary,secondary):
        self.provider,self.primary,self.secondary=provider,primary,tuple(secondary)
        super().__init__('host Windows resource responsibility unresolved')
    def __reduce__(self):raise TypeError('live provider failure cannot be serialized')


def require(value,message):
    if not value:raise ValueError(message)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def creator():return os.getpid(),get_ident()


def decode(raw,cap=131072):
    require(type(raw) is bytes and 0<len(raw)<=cap,'bounded immutable record')
    def unique(items):
        result={}
        for key,value in items:require(key not in result,'duplicate key');result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=unique);require(canonical(value)==raw,'canonical record');return value


def _api(library):
    require(os.name=='nt' and C.sizeof(C.c_void_p)==8,'Windows x64 provider')
    signatures={
        'CreateFileMappingW':([HANDLE,C.c_void_p,DWORD,DWORD,DWORD,W.LPCWSTR],HANDLE),
        'CreateMutexW':([C.c_void_p,W.BOOL,W.LPCWSTR],HANDLE),
        'MapViewOfFile':([HANDLE,DWORD,DWORD,DWORD,SIZE_T],C.c_void_p),
        'UnmapViewOfFile':([C.c_void_p],W.BOOL),
        'VirtualQuery':([C.c_void_p,C.POINTER(_MemoryInfo),SIZE_T],SIZE_T),
        'ReleaseMutex':([HANDLE],W.BOOL),
        'CreateJobObjectW':([C.c_void_p,W.LPCWSTR],HANDLE),
        'SetInformationJobObject':([HANDLE,C.c_int,C.c_void_p,DWORD],W.BOOL),
        'QueryInformationJobObject':([HANDLE,C.c_int,C.c_void_p,DWORD,C.c_void_p],W.BOOL),
        'InitializeProcThreadAttributeList':([C.c_void_p,DWORD,DWORD,C.POINTER(SIZE_T)],W.BOOL),
        'UpdateProcThreadAttribute':([C.c_void_p,DWORD,SIZE_T,C.c_void_p,SIZE_T,C.c_void_p,C.c_void_p],W.BOOL),
        'DeleteProcThreadAttributeList':([C.c_void_p],None),
        'CreateProcessW':([W.LPCWSTR,W.LPWSTR,C.c_void_p,C.c_void_p,W.BOOL,DWORD,C.c_void_p,W.LPCWSTR,
            C.POINTER(_StartupEx),C.POINTER(_ProcessInfo)],W.BOOL),
        'IsProcessInJob':([HANDLE,HANDLE,C.POINTER(W.BOOL)],W.BOOL),
        'GetProcessTimes':([HANDLE]+[C.POINTER(W.FILETIME)]*4,W.BOOL),
        'GetProcessId':([HANDLE],DWORD),
        'GetProcessIdOfThread':([HANDLE],DWORD),
        'GetThreadId':([HANDLE],DWORD),
        'GetHandleInformation':([HANDLE,C.POINTER(DWORD)],W.BOOL),
        'QueryFullProcessImageNameW':([HANDLE,DWORD,W.LPWSTR,C.POINTER(DWORD)],W.BOOL),
        'OpenProcess':([DWORD,W.BOOL,DWORD],HANDLE),
        'ResumeThread':([HANDLE],DWORD),
        'WaitForSingleObject':([HANDLE,DWORD],DWORD),
        'TerminateJobObject':([HANDLE,W.UINT],W.BOOL),
        'CloseHandle':([HANDLE],W.BOOL),
    }
    rows=[]
    for name,(args,result) in signatures.items():
        fn=getattr(library,name);fn.argtypes=args;fn.restype=result
        rows.append((name,fn,tuple(args),result))
    return tuple(rows)


class WindowsResources:
    __slots__=('_root',)
    def __new__(cls,*args,**kwargs):raise NativeUnavailable('source-authenticated Windows provider issuer closed')
    def __setattr__(self,name,value):raise TypeError('held provider')
    def __delattr__(self,name):raise TypeError('held provider')
    def __reduce__(self):raise TypeError('live provider cannot be serialized')
    def __copy__(self):raise TypeError('live provider cannot be copied')
    def __deepcopy__(self,memo):raise TypeError('live provider cannot be copied')


def open_windows_resources(*args,**kwargs):
    raise NativeUnavailable('external root/Native authorization and full host provider not bound')


def _mechanical_resources(owner,started,deadline,clock):
    raise NativeUnavailable('no production Windows provider issuer')
    require(type(started) is type(deadline) is float and 0<started<deadline==started+180.0,'original invocation clock')
    library=C.WinDLL('kernel32',use_last_error=True)
    provider=object.__new__(WindowsResources)
    root=dict(provider=provider,owner=owner,creator=creator(),thread=current_thread(),api=_api(library),library=library,clock=clock,
        started=started,deadline=deadline,last=[started],handles={name:None for name in NAMES},
        states={name:['IDLE',0] for name in NAMES},descriptor=[None],header=[None],header_state=['IDLE',0],child=[None],
        info=_ProcessInfo(),attributes=[None,'IDLE',None],attribute_delete=['IDLE',0],
        creation=['IDLE',0],endpoint=['IDLE',0],resume=['IDLE',0],termination=['IDLE',0],
        mutex=['IDLE',0],quiet=['IDLE',0,None],members={},member_records=[],pending=[None],census_failure=[None],errors=[],busy=[None],operation_base=[0],reentry=[0])
    object.__setattr__(provider,'_root',tuple(root.items()))
    _time(root,True);return provider


def _root(provider):
    require(type(provider) is WindowsResources,'exact Windows resource provider')
    root=dict(object.__getattribute__(provider,'_root'))
    require(root['provider'] is provider and root['creator']==creator() and root['thread'] is current_thread(),'creating Native thread/owner')
    return root


def _call(root,name,*args):
    row=next(row for row in root['api'] if row[0]==name)
    require(tuple(row[1].argtypes)==row[2] and row[1].restype is row[3],'held Native signature drift')
    before=(root['busy'][0],root['reentry'][0]);primary=None
    try:return row[1](*args)
    except BaseException as error:primary=error;raise
    finally:
        if before!=(root['busy'][0],root['reentry'][0]):
            error=ValueError('Native callback reentered provider');root['errors'].append(('native_reentry',error))
            if primary is None:raise error


def _time(root,active):
    before=(root['busy'][0],root['reentry'][0]);now=root['clock']()
    require(before==(root['busy'][0],root['reentry'][0]),'clock callback reentered provider')
    require(type(now) is float and math.isfinite(now) and root['last'][0]<=now,'monotonic provider clock')
    root['last'][0]=now
    if active:require(now<min(root['started']+10.,root['deadline']-15.),'original outer prepare reservation expired')
    return now


def _begin(provider,name,active=True):
    root=_root(provider)
    if root['busy'][0] is not None:
        error=ValueError('reentrant Windows provider');root['errors'].append(('reentry',error));root['reentry'][0]+=1;raise error
    root['operation_base'][0]=root['reentry'][0];root['busy'][0]=name
    try:
        if active:require(root['reentry'][0]==0,'provider reentry is sticky')
        if active:_time(root,True)
        return root
    except BaseException:root['busy'][0]=None;raise


def _end(root):
    operation=root['busy'][0]
    root['busy'][0]=None
    if root['reentry'][0]:
        error=ValueError('swallowed Native provider reentry');root['errors'].append(('operation_reentry',error))
        if (root['reentry'][0]!=root['operation_base'][0] or operation in ('endpoint_create','create_suspended','endpoint_commit','endpoint_read','resume')) and sys.exc_info()[1] is None:raise error


def _check(value):
    if not value:raise C.WinError(C.get_last_error())


def _own(root,name,value):
    require(type(value) is int and value>0,'valid returned Native resource')
    current=root['handles'][name]
    require(current is None or current==value,'Native resource replaced')
    if name!='view':require(value not in (v for k,v in root['handles'].items() if k not in (name,'view') and v is not None),'duplicate kernel HANDLE')
    root['handles'][name]=value


def _noninherit(root,handle):
    flags=DWORD();_check(_call(root,'GetHandleInformation',handle,C.byref(flags)))
    require(flags.value&1==0,'inherited Native HANDLE')


def _recover(root):
    info=root['info'];errors=[]
    for name,value in (('process',info.process),('thread',info.thread)):
        if value:
            try:_own(root,name,value)
            except BaseException as error:errors.append(error)
    if errors:raise errors[0]
    return tuple((name,root['handles'][name]) for name in NAMES)


def resource_snapshot(provider):
    root=_begin(provider,'resource_snapshot',False)
    # Recovery captures only the original preallocated PROCESS_INFORMATION.
    try:
        pending=[]
        try:_recover(root)
        except BaseException as error:root['errors'].append(('snapshot_recovery',error));pending.append('process_info_recovery')
        for name in ('endpoint','creation','header_state','resume','termination','mutex'):
            if root[name][0] in ('ISSUED','RELEASE_ISSUED','UNCERTAIN'):pending.append(name)
        if root['attributes'][1] not in ('IDLE','DELETED'):pending.append('attributes')
        if root['pending'][0] is not None:pending.append('pending_member')
        if root['reentry'][0]:pending.append('provider_reentry')
        if root['census_failure'][0] is not None:pending.append('census_failure')
        return tuple((name,root['handles'][name]) for name in NAMES),tuple(pending)
    finally:_end(root)


def _mirror(root,escrow):
    require(type(escrow) is dict and set(escrow)==set(NAMES),'closed host escrow')
    for name,value in _recover(root):
        require(escrow[name] is None or escrow[name]==value,'host mirror differs from Native root')
        if value is not None:escrow[name]=value


def endpoint_create(provider,escrow,descriptor_raw):
    root=_begin(provider,'endpoint_create');primary=None
    try:
        require(root['endpoint']==['IDLE',0] and all(value is None for value in root['handles'].values()),'one endpoint construction')
        data=decode(descriptor_raw);nonce=data['channel_nonce']
        require(type(nonce) is str and len(nonce)==64 and all(c in '0123456789abcdef' for c in nonce)
            and data['schema']=='staged_saved_F_pre_manifest_descriptor_v1' and data['authority']=='DRAFT_NONAUTHORITATIVE'
            and data['channel_name']=='Local\\saved_F_pre_entry_v1_'+nonce and data['source_epoch']==SOURCE_EPOCH
            and data['role']=='controller' and data['invocation_started']==root['started'] and data['deadline']==root['deadline'],'held endpoint descriptor')
        root['descriptor'][0]=descriptor_raw;root['endpoint'][:]=['ISSUED',1]
        C.set_last_error(0)
        value=_call(root,'CreateFileMappingW',HANDLE(-1),None,4,0,MAP_BYTES,data['channel_name'])
        if value:_own(root,'mapping',value)
        error=C.get_last_error();_check(value);require(error!=183,'mapping already exists');_noninherit(root,value)
        C.set_last_error(0);value=_call(root,'CreateMutexW',None,False,data['channel_name']+'_mutex')
        if value:_own(root,'mutex',value)
        error=C.get_last_error();_check(value);require(error!=183,'mutex already exists');_noninherit(root,value)
        value=_call(root,'MapViewOfFile',root['handles']['mapping'],6,0,0,MAP_BYTES)
        if value:_own(root,'view',value)
        _check(value)
        image=_locked(root,None)
        require(image==bytes(MAP_BYTES),'fresh endpoint must be zero, never overwrite an existing image')
        root['endpoint'][0]='LIVE'
    except BaseException as error:
        primary=error;root['endpoint'][0]='UNCERTAIN';raise
    finally:
        try:
            try:_mirror(root,escrow)
            except BaseException as error:
                root['errors'].append(('endpoint_mirror',error))
                if primary is None:raise
        finally:_end(root)


def _locked(root,frame):
    require(root['mutex'][0]=='IDLE','mutex release uncertainty is sticky')
    result=_call(root,'WaitForSingleObject',root['handles']['mutex'],100)
    if result not in (0,128):
        require(result!=258,'endpoint mutex timeout');raise C.WinError(C.get_last_error())
    root['mutex'][0]='HELD';primary=None
    try:
        require(result==0,'abandoned endpoint mutex')
        view=root['handles']['view']
        first=C.string_at(view,MAP_BYTES);second=C.string_at(view,MAP_BYTES)
        require(first==second,'mapping changed under held mutex')
        if frame is not None:
            require(first==bytes(MAP_BYTES),'header publication is create-only')
            C.memmove(view,frame[:-8],len(frame)-8)
            C.memmove(view+len(frame)-8,frame[-8:],8)
            first=C.string_at(view,MAP_BYTES);require(first==frame+bytes(MAP_BYTES-len(frame)),'header physical readback')
        return first
    except BaseException as error:primary=error;raise
    finally:
        root['mutex'][0]='RELEASE_ISSUED';root['mutex'][1]+=1
        try:_check(_call(root,'ReleaseMutex',root['handles']['mutex']));root['mutex'][0]='IDLE'
        except BaseException as error:
            root['mutex'][0]='UNCERTAIN';root['errors'].append(('release_mutex',error))
            if primary is None:raise


def _environment(raw):
    value=decode(raw)
    require(type(value) is dict and value and all(type(k) is type(v) is str and k and '=' not in k and '\0' not in k+v for k,v in value.items())
        and len({k.upper() for k in value})==len(value),'closed environment')
    return C.create_unicode_buffer('\0'.join(k+'='+value[k] for k in sorted(value,key=str.upper))+'\0\0')


def create_suspended(provider,escrow,argv,cwd,environment_raw,limits_raw):
    root=_begin(provider,'create_suspended');primary=None
    try:
        require(root['endpoint'][0]=='LIVE' and root['creation']==['IDLE',0],'one suspended child construction')
        descriptor=decode(root['descriptor'][0]);limits=decode(limits_raw)
        require(type(argv) is tuple and len(argv)==19 and all(type(a) is str and '\0' not in a for a in argv)
            and argv[:6]==(EXE,'-P','-B','-s','-S','-c') and argv[7:]==('--full-role-pre-entry',descriptor['manifest_path'],
                descriptor['manifest_sha'],descriptor['channel_name'],descriptor['channel_nonce'],'controller',descriptor['request_sha'],
                descriptor['offer_sha'],descriptor['context_sha'],descriptor['ack_sha'],root['started'].hex(),root['deadline'].hex())
            and cwd==str(ROOT),'exact full child launch data')
        require(sha256(argv[6].encode()).hexdigest()==descriptor['transport_pin']['sha256']
            and len(argv[6].encode())==descriptor['transport_pin']['bytes'],'transport bytes relation')
        command_text=subprocess.list2cmdline(argv);require(len(command_text.encode('utf-16-le'))//2+1<=30000,'quoted argv cap')
        require(limits['process_commit_bytes']==1024**3 and limits['job_commit_bytes']==2*1024**3,'original commit caps')
        environment=_environment(environment_raw);command=C.create_unicode_buffer(command_text)
        root['creation'][:]=['ISSUED',1]
        value=_call(root,'CreateJobObjectW',None,None)
        if value:_own(root,'job',value)
        _check(value);_noninherit(root,value)
        config=_Limits();config.basic.flags=0x2000|0x100|0x200
        config.process_memory=limits['process_commit_bytes'];config.job_memory=limits['job_commit_bytes']
        _check(_call(root,'SetInformationJobObject',value,9,C.byref(config),C.sizeof(config)))
        size=SIZE_T();C.set_last_error(0)
        result=_call(root,'InitializeProcThreadAttributeList',None,1,0,C.byref(size))
        require(not result and C.get_last_error()==122 and 0<size.value<=65536,'bounded attribute size query')
        buffer=C.create_string_buffer(size.value);jobs=(HANDLE*1)(value)
        root['attributes'][:]=[buffer,'INIT_ISSUED',jobs]
        _check(_call(root,'InitializeProcThreadAttributeList',buffer,1,0,C.byref(size)))
        root['attributes'][1]='LIVE'
        _check(_call(root,'UpdateProcThreadAttribute',buffer,0,0x2000D,jobs,C.sizeof(jobs),None,None))
        startup=_StartupEx();startup.startup.cb=C.sizeof(startup);startup.attributes=C.cast(buffer,C.c_void_p)
        _check(_call(root,'CreateProcessW',argv[0],command,None,None,False,0x08080404,environment,cwd,C.byref(startup),C.byref(root['info'])))
        _recover(root)
        child=_identity(root)
        require(child['pid']==root['info'].pid and _call(root,'GetThreadId',root['handles']['thread'])==root['info'].tid
            and _call(root,'GetProcessIdOfThread',root['handles']['thread'])==child['pid'],'actual process/thread tuple')
        _noninherit(root,root['handles']['process']);_noninherit(root,root['handles']['thread'])
        path=C.create_unicode_buffer(32768);length=DWORD(32768)
        _check(_call(root,'QueryFullProcessImageNameW',root['handles']['process'],0,path,C.byref(length)))
        require(path.value.casefold()==EXE.casefold(),'child executable image differs')
        root['child'][0]=canonical(child)
        root['creation'][0]='SUSPENDED'
    except BaseException as error:
        primary=error;root['creation'][0]='UNCERTAIN';raise
    finally:
        try:
            try:_mirror(root,escrow)
            except BaseException as error:
                root['errors'].append(('recover',error))
                if primary is None:primary=error
            try:_delete_attributes(root)
            except BaseException as error:
                root['errors'].append(('attributes',error))
                if primary is None:primary=error
            if primary is not None and sys.exc_info()[1] is None:raise primary
        finally:_end(root)


def _delete_attributes(root):
    if root['attributes'][1]=='IDLE':return
    require(root['attributes'][1]=='LIVE' and root['attribute_delete']==['IDLE',0],'attribute initialization/delete unresolved')
    root['attribute_delete'][:]=['ISSUED',1]
    try:_call(root,'DeleteProcThreadAttributeList',root['attributes'][0])
    except BaseException:
        root['attribute_delete'][0]='UNCERTAIN';raise
    root['attribute_delete'][0]='DONE';root['attributes'][1]='DELETED'


def _identity_handle(root,handle):
    pid=_call(root,'GetProcessId',handle);require(type(pid) is int and 0<pid<2**32,'actual PID')
    times=[W.FILETIME() for _ in range(4)]
    _check(_call(root,'GetProcessTimes',handle,*(C.byref(t) for t in times)))
    creation=times[0].dwLowDateTime|(times[0].dwHighDateTime<<32);require(0<creation<2**64,'actual creation FILETIME')
    return dict(pid=pid,creation_filetime=creation)


def _identity(root):
    _recover(root);handle=root['handles']['process'];require(handle is not None and root['handles']['job'] is not None,'held process and Job')
    inside=W.BOOL();_check(_call(root,'IsProcessInJob',handle,root['handles']['job'],C.byref(inside)));require(inside.value,'process not in held Job')
    identity=_identity_handle(root,handle)
    if root['child'][0] is not None:require(canonical(identity)==root['child'][0],'retained child identity changed')
    else:
        root['child'][0]=canonical(identity)
        key=identity['pid'],identity['creation_filetime']
        root['members'][key]=[0,handle,key,root['states']['process']]
    return identity


def child_identity(provider,escrow):
    root=_begin(provider,'child_identity',False)
    try:_mirror(root,escrow);return _identity(root)
    finally:_end(root)


def endpoint_commit(provider,escrow,header):
    root=_begin(provider,'endpoint_commit')
    try:
        _mirror(root,escrow);require(root['header_state']==['IDLE',0] and root['creation'][0]=='SUSPENDED','one header after suspended construction')
        require(type(header) is bytes and len(header)==4096 and header[-8:]==b'FEPv1OK!','closed endpoint header')
        length=int.from_bytes(header[:4],'little');require(0<length<=4052,'header length')
        raw=header[4:4+length];value=decode(raw)
        require(header[4+length:-40]==bytes(4052-length) and header[-40:-8]==sha256(raw).digest(),'header padding/hash')
        child=_identity(root);descriptor=decode(root['descriptor'][0])
        require(value==dict(schema='staged_saved_F_pre_manifest_header_v1',nonce=descriptor['channel_nonce'],descriptor=descriptor,
            owner_pid=child['pid'],owner_creation_filetime=child['creation_filetime'],slots=16,slot_bytes=4096),'actual child header binding')
        root['header_state'][:]=['ISSUED',1]
        _locked(root,header);root['header'][0]=header;root['header_state'][0]='DONE';return True
    except BaseException:
        if root['header_state'][0]=='ISSUED':root['header_state'][0]='UNCERTAIN'
        raise
    finally:_end(root)


def endpoint_read(provider,escrow):
    root=_begin(provider,'endpoint_read')
    try:
        _mirror(root,escrow);require(root['header_state']==['DONE',1] and root['header'][0] is not None,'committed header required')
        image=_locked(root,None);require(image[:4096]==root['header'][0],'committed header drift');return image
    finally:_end(root)


def resume(provider,escrow):
    root=_begin(provider,'resume')
    try:
        _mirror(root,escrow);_identity(root)
        require(root['resume']==['IDLE',0] and root['creation'][0]=='SUSPENDED' and root['header'][0] is not None,'one bound suspended resume')
        root['resume'][:]=['ISSUED',1]
        result=_call(root,'ResumeThread',root['handles']['thread']);require(result==1,'original suspend count one')
        root['resume'][0]='DONE';return result
    except BaseException:
        if root['resume'][0]=='ISSUED':root['resume'][0]='UNCERTAIN'
        raise
    finally:_end(root)


def _pids(root):
    data=C.create_string_buffer(8+1024*C.sizeof(SIZE_T))
    _check(_call(root,'QueryInformationJobObject',root['handles']['job'],3,data,len(data),None))
    assigned=DWORD.from_buffer(data,0).value;count=DWORD.from_buffer(data,4).value
    require(assigned==count and count<=1024,'complete bounded Job process list')
    values=list((SIZE_T*count).from_buffer(data,8))
    require(len(set(values))==count and all(0<p<2**32 for p in values),'unique Job PIDs');return values


def _closed_handle(root,handle):
    flags=DWORD();C.set_last_error(0);ok=_call(root,'GetHandleInformation',handle,C.byref(flags))
    require(not ok and C.get_last_error()==6,'closed HANDLE invalid-handle witness')


def _member_close(root,record):
    require(any(record is row for row in root['member_records']),'original member acquisition generation')
    handle=record[1];state=record[3]
    require(state==['IDLE',0],'member close already issued')
    state[:]=['ISSUED',1]
    try:_check(_call(root,'CloseHandle',handle));_closed_handle(root,handle)
    except BaseException:
        state[0]='UNCERTAIN';raise
    state[0]='CLOSED'


def _capture_members(root,deadline=None):
    deadline=root['deadline'] if deadline is None else deadline
    require(_time(root,False)<=deadline,'member census deadline')
    for pid in _pids(root):
        require(_time(root,False)<=deadline,'member census deadline')
        if any(identity[0]==pid and _call(root,'WaitForSingleObject',record[1],0)==258 for identity,record in root['members'].items()):continue
        require(len(root['members'])<1024 and len(root['member_records'])<1024 and root['pending'][0] is None,'retained member/acquisition record cap')
        handle=_call(root,'OpenProcess',0x100000|0x1000,False,pid)
        if not handle:
            if C.get_last_error() in (87,1168):continue
            _check(handle)
        record=[len(root['member_records'])+1,handle,None,['IDLE',0]]
        root['member_records'].append(record);root['pending'][0]=record;primary=None
        try:
            require(_time(root,False)<=deadline,'OpenProcess exhausted census deadline')
            _noninherit(root,handle);inside=W.BOOL()
            _check(_call(root,'IsProcessInJob',handle,root['handles']['job'],C.byref(inside)));require(inside.value,'observed process left held Job')
            value=_identity_handle(root,handle);require(value['pid']==pid,'opened member PID changed')
            require(_time(root,False)<=deadline,'member identity exhausted census deadline')
            key=value['pid'],value['creation_filetime']
            record[2]=key
            if key not in root['members']:
                root['members'][key]=record;root['pending'][0]=None
        except BaseException as error:primary=error;raise
        finally:
            if root['pending'][0] is not None:
                try:_member_close(root,root['pending'][0]);root['pending'][0]=None
                except BaseException as error:
                    root['errors'].append(('pending_member',error))
                    if primary is None:raise
    require(_time(root,False)<=deadline,'member census deadline')


def capture_members(provider):
    root=_begin(provider,'capture_members',False);attempted=False
    try:
        require(root['reentry'][0]==0,'sticky failure cannot acquire new member responsibilities')
        now=_time(root,False);require(now<root['deadline'],'original member census deadline')
        require(root['termination']==['IDLE',0] and root['quiet']==['IDLE',0,None],'active census before terminal observation')
        attempted=True;_capture_members(root,min(root['deadline'],now+STOP_CENSUS_SECONDS))
    except BaseException as error:
        if attempted and root['census_failure'][0] is None:root['census_failure'][0]=error
        raise
    finally:_end(root)


def terminate(provider,escrow):
    root=_begin(provider,'terminate',False);primary=None
    try:
        _mirror(root,escrow);require(root['handles']['job'] is not None and root['termination']==['IDLE',0],'one held Job terminate')
        try:
            if root['handles']['process'] is not None:_identity(root)
            _capture_members(root,min(root['deadline'],_time(root,False)+STOP_CENSUS_SECONDS))
        except BaseException as error:primary=error;root['errors'].append(('pre_terminate_census',error))
        root['termination'][:]=['ISSUED',1]
        try:_check(_call(root,'TerminateJobObject',root['handles']['job'],0xE002));root['termination'][0]='DONE'
        except BaseException as error:
            root['termination'][0]='UNCERTAIN'
            if primary is None:primary=error
            else:root['errors'].append(('termination',error))
        if primary is not None:raise primary
        return True
    finally:_end(root)


def quiet(provider,escrow,deadline):
    root=_begin(provider,'quiet',False)
    try:
        _mirror(root,escrow);now=_time(root,False)
        require(type(deadline) is float and now<=deadline<=min(root['deadline'],now+5.),'remaining original quiet budget')
        require(root['handles']['job'] is not None and root['termination'][0] in ('DONE','UNCERTAIN')
            and root['quiet']==['IDLE',0,None],'one quiet after termination')
        root['quiet'][:]=['ISSUED',1,None]
        if root['handles']['process'] is not None:_identity(root)
        _capture_members(root,deadline)
        for record in root['members'].values():
            remaining=deadline-_time(root,False);require(remaining>=0,'quiet deadline expired')
            require(_call(root,'WaitForSingleObject',record[1],int(remaining*1000))==0,'retained member not signaled')
        accounting=_Accounting();_check(_call(root,'QueryInformationJobObject',root['handles']['job'],1,C.byref(accounting),C.sizeof(accounting),None))
        final=_pids(root)
        second=_Accounting();_check(_call(root,'QueryInformationJobObject',root['handles']['job'],1,C.byref(second),C.sizeof(second),None))
        require((second.active,second.total)==(accounting.active,accounting.total),'Job accounting changed across final inventory')
        require(accounting.active==0 and final==[] and accounting.total==len(root['members']) and root['pending'][0] is None,'complete held Job quiet inventory')
        require(_time(root,False)<=deadline,'quiet exceeded original deadline')
        identities=[dict(pid=p,creation_filetime=c) for p,c in sorted(root['members'])]
        result=dict(complete=True,job_handle=root['handles']['job'],member_identities=identities,active_processes=0,
            retained_handles_signaled=True,observed_total=accounting.total,observed_count=len(identities),final_pids=[])
        root['quiet'][:]=['DONE',1,canonical(result)];return result
    except BaseException:
        if root['quiet'][0]=='ISSUED':root['quiet'][0]='UNCERTAIN'
        raise
    finally:_end(root)


def _witness(root,name,handle):
    if name!='view':_closed_handle(root,handle);return
    info=_MemoryInfo();require(_call(root,'VirtualQuery',handle,C.byref(info),C.sizeof(info))==C.sizeof(info)
        and info.state==0x10000,'unmapped view MEM_FREE witness')


def _close_aux(root):
    errors=[]
    for record in root['member_records']:
        if record[3][0]=='CLOSED':continue
        try:_member_close(root,record)
        except BaseException as error:errors.append(('member_close',error))
    if root['pending'][0] is not None and root['pending'][0][3][0]=='CLOSED':root['pending'][0]=None
    return errors


def close(provider,name,handle):
    root=_begin(provider,'close_'+name,False);errors=[]
    try:
        _recover(root);require(name in NAMES and root['handles'][name]==handle and handle is not None,'original resource close')
        require(not any(root['handles'][name] is not None for name in ('job','process','thread'))
            or root['quiet'][0]=='DONE','retain all resources until original Job/child quiet')
        state=root['states'][name];require(state==['IDLE',0],'close already issued')
        if name in ('process','job'):errors.extend(_close_aux(root))
        if name=='mutex':require(root['mutex'][0]=='IDLE','mutex ownership unresolved')
        state[:]=['ISSUED',1]
        try:_check(_call(root,'UnmapViewOfFile' if name=='view' else 'CloseHandle',handle));_witness(root,name,handle)
        except BaseException as error:state[0]='UNCERTAIN';errors.append(('close_'+name,error))
        else:state[0]='CLOSED'
        if name=='mapping' and root['attributes'][1] not in ('IDLE','DELETED'):
            errors.append(('attributes_unresolved',ValueError('attribute initialization/delete unresolved')))
        if errors:
            root['errors'].extend(errors);raise ProviderUnresolved(provider,None,errors)
        return True
    finally:_end(root)


def closed_witness(provider,name,handle):
    root=_begin(provider,'closed_witness',False)
    try:
        require(name in NAMES and root['handles'][name]==handle and root['states'][name]==['CLOSED',1],'issued close ledger')
        try:_witness(root,name,handle)
        except BaseException:
            root['states'][name][0]='UNCERTAIN';raise
    finally:_end(root)
    return True
