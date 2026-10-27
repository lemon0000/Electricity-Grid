"""Local, development-only source lease before any Source49 read or compile."""
import sys

_MODULE_CODE = sys._getframe().f_code
_RELEASED = False
_EARLY = None
_RUNTIME = 'D:\\Miniconda3\\envs\\compute'
_PATHS = (_RUNTIME+'\\python312.zip', _RUNTIME+'\\DLLs', _RUNTIME+'\\Lib', _RUNTIME)
_PYTHON = '3.12.12 | packaged by Anaconda, Inc. | (main, Oct 21 2025, 20:05:38) [MSC v.1929 64 bit (AMD64)]'
if __name__ == '__main__':
    _flags = sys.flags
    _prefix_ok = (len(sys.argv)==4 and sys.argv[0]=='-c' and sys.argv[1]=='--pre-entry-lease'
        and len(sys.argv[3])==64 and all(c in '0123456789abcdef' for c in sys.argv[3])
        and _flags.safe_path and _flags.no_site and _flags.no_user_site and _flags.dont_write_bytecode
        and not _flags.optimize and not _flags.hash_randomization and not _flags.isolated and not _flags.ignore_environment
        and sys.version==_PYTHON and sys.executable.replace('/','\\').casefold()==(_RUNTIME+'\\python.exe').casefold()
        and tuple(p.replace('/','\\').rstrip('\\').casefold() for p in sys.path)==tuple(p.casefold() for p in _PATHS))
    if not _prefix_ok:
        print('{"status":"PREFIX_REJECTED","self_handles_opened":0}'); raise SystemExit(1)
    _frame = b'SAVED_PRE_ENTRY_V1:'+sys.argv[3].encode('ascii')+b'\n'
    if sys.stdin.buffer.read(len(_frame))!=_frame or sys.stdin.buffer.read(1)!=b'':
        print('{"status":"RELEASE_REJECTED","self_handles_opened":0}'); raise SystemExit(1)
    _RELEASED = True
    _EARLY_TOKEN=object()
    _EARLY = dict(active=True,installation=False,imports=[],opens=[],blocked=[],sources_allowed=False,
        initial=[(n,getattr(getattr(m,'__spec__',None),'origin',None),type(getattr(m,'__loader__',None)).__module__+'.'+type(getattr(m,'__loader__',None)).__qualname__) for n,m in sorted(sys.modules.items())])
    def _early_audit(event,args):
        if not _EARLY['active']: return
        if event=='electricity_grid.pre_entry.early_install':
            if len(args)!=1 or args[0] is not _EARLY_TOKEN or _EARLY['installation']: raise RuntimeError('early audit sentinel rejected')
            _EARLY['installation']=True; return
        if event=='import':
            if len(_EARLY['imports'])>=2048: raise RuntimeError('early import event cap')
            _EARLY['imports'].append((args[0],args[1] if isinstance(args[1],str) else None))
            if any(args[0]==p or args[0].startswith(p+'.') for p in ('src','experiments','tests','numpy','scipy','pyomo','highspy')):
                _EARLY['blocked'].append('project_import'); raise RuntimeError('early project import rejected')
        if event=='open':
            name,mode,flags=args[:3]
            if isinstance(name,str):
                if len(_EARLY['opens'])>=4096: raise RuntimeError('early open event cap')
                path=name.replace('\\','/').casefold(); _EARLY['opens'].append(name)
                root='d:/cuhksz/research project/electricity-grid/'
                transport=sys.argv[2].replace('\\','/').casefold()
                profile=root+'results/tables/staged_rts24_saved_fresh_runtime_stk_v1_non_authoritative/startup_profile.json'
                if not _EARLY['sources_allowed'] and path.startswith(root) and path not in (transport,profile):
                    _EARLY['blocked'].append('project_open'); raise RuntimeError('early project open rejected')
                if not _EARLY['sources_allowed'] and not (len(path)>2 and path[1]==':' or path.startswith('//')):
                    _EARLY['blocked'].append('relative_open'); raise RuntimeError('early relative open rejected')
            if isinstance(mode,str) and any(c in mode for c in 'wax+') or isinstance(flags,int) and flags&0x30b:
                _EARLY['blocked'].append('write'); raise RuntimeError('early write rejected')
        if event in ('subprocess.Popen','os.system','os.posix_spawn') or event.startswith(('os.spawn','os.exec')):
            _EARLY['blocked'].append('process'); raise RuntimeError('early process rejected')
        if event in ('os.remove','os.rmdir','os.rename','os.mkdir','os.link','os.symlink','os.chmod','os.truncate','os.utime'):
            _EARLY['blocked'].append('mutation'); raise RuntimeError('early mutation rejected')
    sys.addaudithook(_early_audit)
    sys.audit('electricity_grid.pre_entry.early_install',_EARLY_TOKEN)
    if not _EARLY['installation']:
        print('{"status":"EARLY_GUARD_REJECTED","self_handles_opened":0}'); raise SystemExit(1)

import builtins
import dataclasses as _startup_dataclasses
import ctypes as C
from ctypes import wintypes as W
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import subprocess
from threading import get_ident
from types import FunctionType, CodeType

ROOT = Path('D:/CUHKSZ/Research Project/electricity-grid')
EXE = Path(_RUNTIME)/'python.exe'
ENTRY = 'experiments/staged_rts24_saved_fresh_adoption_v1.py'
SOURCE_SHA = 'acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'
TCB_PATHS = tuple(str(Path(_RUNTIME)/n) for n in ('python312.dll','DLLs/_ctypes.pyd','Lib/ctypes/__init__.py','Lib/ctypes/wintypes.py','Lib/subprocess.py','Lib/encodings/__init__.py'))
STARTUP_ABSENT = tuple(str(Path(_RUNTIME)/n) for n in ('python312._pth','python._pth','pyvenv.cfg','python312.zip'))+(str(Path(_RUNTIME).parent/'pyvenv.cfg'),)
_ATTEMPTED = False
FALSE_GATES = dict(external_expected_truth_verified=False, upstream_owner_verified=False,
    startup_tcb_authenticated=False, independent_root_verified=False, native_behavior_verified=False,
    parent_independently_authenticated_python_object_graph=False, full_runtime_binding_verified=False,
    full_P1_content_verified=False, role_bootstrap=False, permit_issued=False, native_authorized=False,
    F_launch_admitted=False, actual_F=False, run_authority=False, scientific_evidence_adopted=False,
    resource_admission=False, formal_result=False, production_seal=False)


def require(value, message):
    if not value: raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def decode(raw):
    require(type(raw) is bytes and len(raw)<=131072, 'manifest byte cap')
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result, 'duplicate manifest key'); result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=pairs)
    require(canonical(value)==raw, 'canonical manifest required')
    return value


def check_plan(raw):
    plan=decode(raw)
    fields='schema authority nonce source_pins source_epoch bootstrap_pin executable_pin python environment cwd initial_paths selected_runtime_file_observations startup_absent startup_profile namespace_helper import_helper import_policy import_profile case'
    require(type(plan) is dict and set(plan)==set(fields.split()), 'closed manifest fields')
    require(plan['schema']=='staged_saved_F_runtime_handoff_manifest_v1' and plan['authority']=='DRAFT_NONAUTHORITATIVE', 'manifest schema')
    require(type(plan['nonce']) is str and len(plan['nonce'])==32 and all(c in '0123456789abcdef' for c in plan['nonce']), 'manifest nonce')
    require(plan['source_epoch']==SOURCE_SHA and type(plan['source_pins']) is dict and len(plan['source_pins'])==49
        and len(canonical(plan['source_pins']))==6571 and pin(canonical(plan['source_pins']))['sha256']==SOURCE_SHA, 'fixed development Source49 map')
    require(plan['python']==_PYTHON and plan['cwd']==str(ROOT) and plan['initial_paths']==list(_PATHS), 'manifest startup values')
    require(plan['executable_pin']==dict(bytes=104264,sha256='4a7d81f72d979c088c653b1da12c2f2d81da66bdf8074753c6a9b154d9c86116'), 'fixed EXE pin')
    require(type(plan['environment']) is dict and all(type(k) is type(v) is str for k,v in plan['environment'].items()), 'manifest environment')
    allowed={'PATH','SYSTEMROOT','WINDIR','TEMP','TMP','USERPROFILE','PYTHONHASHSEED','PYTHONDONTWRITEBYTECODE','PYTHONNOUSERSITE','OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'}
    require(set(k.upper() for k in plan['environment'])<=allowed and len({k.upper() for k in plan['environment']})==len(plan['environment']), 'environment whitelist')
    for name,value in dict(PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1').items():
        require(plan['environment'].get(name)==value, 'fixed environment value')
    require(plan['case'] in ('discovery','import_discovery','normal','precommit','postcommit','blocked_installation','handoff_middle','M_only','after_D'), 'closed diagnostic case')
    require(type(plan['selected_runtime_file_observations']) is dict and set(plan['selected_runtime_file_observations'])==set(TCB_PATHS)
        and plan['startup_absent']==list(STARTUP_ABSENT), 'selected runtime observations')
    require(plan['startup_profile'] is None if plan['case'] =='discovery' else type(plan['startup_profile']) is dict and set(plan['startup_profile'])=={'path','pin'},'two-stage startup profile')
    require(type(plan['namespace_helper']) is dict and set(plan['namespace_helper'])=={'path','pin'} and plan['namespace_helper']['path']==str(ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_v2.py'),'fixed namespace helper reference')
    for field in ('import_helper','import_policy'):
        require(type(plan[field]) is dict and set(plan[field])=={'path','pin'},'fixed runtime attachment reference')
    require(plan['import_profile'] is None if plan['case'] in ('discovery','import_discovery') else type(plan['import_profile']) is dict and set(plan['import_profile'])=={'path','pin'},'two-stage B_S import profile')
    return plan


def read_file(path, expected, *, links=False):
    path=Path(path)
    def ordinary(item, directory=False):
        info=item.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400, 'ordinary filesystem path')
        require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and (links or info.st_nlink==1), 'regular filesystem object')
        return info
    def identity(info): return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns
    def parents(): return tuple((str(p),s.st_dev,s.st_ino) for p in reversed(tuple(path.parents)) for s in (ordinary(p,True),))
    require(type(expected) is dict and set(expected)=={'bytes','sha256'} and type(expected['bytes']) is int and 0<=expected['bytes']<=8*1024**2, 'bounded file pin')
    chain=parents(); before=identity(ordinary(path)); require(before[2]==expected['bytes'], 'file size differs')
    with path.open('rb',buffering=0) as stream:
        require(identity(os.fstat(stream.fileno()))==before, 'opened file identity differs')
        raw=stream.read(expected['bytes']+1)
        require(identity(os.fstat(stream.fileno()))==before, 'read identity differs')
    require(identity(ordinary(path))==before and parents()==chain and pin(raw)==expected, 'file bookend differs')
    return raw


def kernel_api():
    api=C.WinDLL('kernel32',use_last_error=True)
    definitions={
        'GetCurrentProcessId':((),W.DWORD),'GetCurrentThreadId':((),W.DWORD),
        'OpenProcess':((W.DWORD,W.BOOL,W.DWORD),W.HANDLE),'OpenThread':((W.DWORD,W.BOOL,W.DWORD),W.HANDLE),
        'GetProcessId':((W.HANDLE,),W.DWORD),'GetThreadId':((W.HANDLE,),W.DWORD),'GetProcessIdOfThread':((W.HANDLE,),W.DWORD),
        'GetProcessTimes':((W.HANDLE,)+(C.POINTER(W.FILETIME),)*4,W.BOOL),
        'GetThreadTimes':((W.HANDLE,)+(C.POINTER(W.FILETIME),)*4,W.BOOL),
        'QueryFullProcessImageNameW':((W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)),W.BOOL),
        'GetCommandLineW':((),W.LPWSTR),'GetHandleInformation':((W.HANDLE,C.POINTER(W.DWORD)),W.BOOL),'CloseHandle':((W.HANDLE,),W.BOOL)}
    held={}
    for name,(args,result) in definitions.items():
        fn=getattr(api,name); fn.argtypes=list(args); fn.restype=result; held[name]=(fn,args,result)
    return api,held


def checked_call(held,name,*args):
    fn,types,result=held[name]
    require(tuple(fn.argtypes)==types and fn.restype is result, 'kernel signature differs')
    value=fn(*args)
    if not value: raise C.WinError(C.get_last_error())
    return value


def creation(held,name,handle):
    values=[W.FILETIME() for _ in range(4)]
    checked_call(held,name,handle,*(C.byref(v) for v in values))
    return values[0].dwLowDateTime | values[0].dwHighDateTime<<32


class LocalPreEntryUnresolved(RuntimeError):
    def __init__(self,owner,primary,secondary):
        super().__init__('local pre-entry ownership or cleanup unresolved')
        self.owner,self.primary,self.secondary=owner,primary,tuple(secondary)
    def __reduce__(self): raise TypeError('local resource failure is not transferable')


class LocalPreEntryConstructionFailed(RuntimeError):
    def __init__(self,owner,primary,secondary):
        super().__init__('local pre-entry construction failed')
        self.owner,self.primary,self.secondary=owner,primary,tuple(secondary)
    def __reduce__(self): raise TypeError('local construction evidence cannot be serialized')


class _Resource:
    def __init__(self,owner,guard):
        self.api,self.held=kernel_api(); self.owner=owner; self.guard=guard
        self.creator=(checked_call(self.held,'GetCurrentProcessId'),get_ident(),checked_call(self.held,'GetCurrentThreadId'))
        self.pending=[None,None]; self.close_calls=[0,0]; self.phase='OPENING'; self.observation=None
        self._close_impl=type(self).close
        self._C,self._W,self._tuple,self._getpid,self._get_ident,self._reject=C,W,tuple,os.getpid,get_ident,ValueError
        self._byref,self._set_error,self._get_error,self._DWORD,self._WinError=C.byref,C.set_last_error,C.get_last_error,W.DWORD,C.WinError
        self._any,self._unresolved,self._early=any,LocalPreEntryUnresolved,_EARLY
        self.cleanup_code=self._close_impl.__code__
    def open(self):
        self.pending[0]=(checked_call(self.held,'OpenProcess',0x1000,False,self.creator[0]),'live')
        sys.audit('electricity_grid.pre_entry.process_handle_opened',self)
        self.pending[1]=(checked_call(self.held,'OpenThread',0x0800,False,self.creator[2]),'live')
        self.observation=self.snapshot(); self.phase='LIVE'; self.guard['self_live']=True
        if self._early is not None: self._early['sources_allowed']=True
        self.guard['events'].append('self_handles_live')
    def snapshot(self):
        require(self.creator==(checked_call(self.held,'GetCurrentProcessId'),get_ident(),checked_call(self.held,'GetCurrentThreadId')), 'foreign pre-entry creator')
        p,t=(v[0] for v in self.pending)
        for handle in (p,t):
            flags=W.DWORD(); checked_call(self.held,'GetHandleInformation',handle,C.byref(flags)); require(flags.value==0,'inheritable self HANDLE')
        require(checked_call(self.held,'GetProcessId',p)==checked_call(self.held,'GetProcessIdOfThread',t)==self.creator[0]
            and checked_call(self.held,'GetThreadId',t)==self.creator[2], 'self kernel identity differs')
        image=C.create_unicode_buffer(32768); size=W.DWORD(len(image))
        checked_call(self.held,'QueryFullProcessImageNameW',p,0,image,C.byref(size))
        return dict(pid=self.creator[0],tid=self.creator[2],process_creation_filetime=creation(self.held,'GetProcessTimes',p),
            thread_creation_filetime=creation(self.held,'GetThreadTimes',t),image_path=image.value,
            command_line_sha=pin(checked_call(self.held,'GetCommandLineW').encode('utf-8')))
    def close(self,owner,primary=None):
        if self.owner is not owner or self.creator[:2]!=(self._getpid(),self._get_ident()): raise self._reject('cleanup owner differs')
        errors=[]
        for index in (1,0):
            row=self.pending[index]
            if row is None: continue
            handle,state=row
            if state!='live': errors.append(('uncertain_handle',index)); continue
            try:
                close,types,result=self.held['CloseHandle']
                if self._tuple(close.argtypes)!=types or close.restype is not result: raise self._reject('close signature differs')
                self.close_calls[index]+=1
                if not close(handle): raise self._WinError(self._get_error())
                self.pending[index]=(handle,'close_issued')
                fn,args,result=self.held['GetHandleInformation']
                if self._tuple(fn.argtypes)!=args or fn.restype is not result: raise self._reject('close witness signature')
                flags=self._DWORD(); self._set_error(0)
                if fn(handle,self._byref(flags)) or self._get_error()!=6: raise self._reject('close witness unknown')
                self.pending[index]=None
            except BaseException as error: errors.append(('thread' if index else 'process',error))
        self.guard['self_live']=False
        if self._early is not None: self._early['sources_allowed']=False
        self.phase='CLOSED' if not self._any(self.pending) else 'UNRESOLVED'
        if self.phase=='CLOSED': self.guard['events'].append('self_handles_closed')
        if errors: raise self._unresolved(owner,primary,errors) from primary


def control_image():
    return (tuple(sys.argv),tuple(sys.orig_argv),tuple(sys.path),canonical(dict(os.environ)),os.getcwd(),
        id(sys.modules),id(sys.meta_path),tuple(map(id,sys.meta_path)),id(sys.path_hooks),tuple(map(id,sys.path_hooks)),id(sys.path_importer_cache))


def startup_profile(plan):
    """A conditional distribution profile; never authenticates loaded Python/native code."""
    require(_EARLY is not None and not _EARLY['sources_allowed'] and not _EARLY['blocked'],'startup event window differs')
    api=C.WinDLL('kernel32',use_last_error=True)
    enum=api.K32EnumProcessModules; enum.argtypes=[W.HANDLE,C.POINTER(W.HMODULE),W.DWORD,C.POINTER(W.DWORD)]; enum.restype=W.BOOL
    filename=api.GetModuleFileNameW; filename.argtypes=[W.HMODULE,W.LPWSTR,W.DWORD]; filename.restype=W.DWORD
    current=api.GetCurrentProcess; current.argtypes=[]; current.restype=W.HANDLE
    array=(W.HMODULE*1024)(); needed=W.DWORD()
    require(enum(current(),array,C.sizeof(array),C.byref(needed)) and needed.value<=C.sizeof(array),'native module census cap')
    native=[]
    for handle in array[:needed.value//C.sizeof(W.HMODULE)]:
        buffer=C.create_unicode_buffer(32768); size=filename(handle,buffer,len(buffer))
        require(0<size<len(buffer),'native module origin unavailable'); native.append(buffer.value)
    modules=[]; disk=set()
    for name,module in sorted(sys.modules.items()):
        spec=getattr(module,'__spec__',None); origin=getattr(spec,'origin',None); loader=getattr(module,'__loader__',None)
        modules.append((name,origin,type(loader).__module__+'.'+type(loader).__qualname__))
        if type(origin) is str and os.path.isabs(origin):
            require(Path(origin).is_relative_to(Path(_RUNTIME)),'Python module outside controlled distribution')
            disk.add(origin)
    opened=tuple(_EARLY['opens'])
    for path in (*opened,*native):
        if os.path.isabs(path) and Path(path).is_relative_to(Path(_RUNTIME)) and Path(path).is_file(): disk.add(path)
    require(len(disk)<=128,'startup disk origin cap')
    files={}; total=0
    for path in sorted(disk,key=str.casefold):
        info=Path(path).lstat(); require(stat.S_ISREG(info.st_mode) and info.st_size<=8*1024**2,'startup disk file cap')
        with open(path,'rb',buffering=0) as stream: raw=stream.read(info.st_size+1)
        expected=pin(raw); require(expected['bytes']==info.st_size,'startup file size drift')
        read_file(path,expected,links=True); files[path]=expected; total+=len(raw)
        require(total<=32*1024**2,'startup aggregate disk cap')
    return dict(schema='staged_saved_F_conditional_startup_profile_v1',
        conditional_tcb_assumption_id='controlled_compute_CPython_3_12_12_windows_vm_stdlib_native_kernel_v1',
        bootstrap_pin=plan['bootstrap_pin'],environment_sha=pin(canonical(dict(os.environ))),cwd=os.getcwd(),paths=list(sys.path),
        initial_modules=_EARLY['initial'],ordered_import_events=list(_EARLY['imports']),module_origins=modules,
        disk_file_observations=files,native_origin_boundaries=sorted(native,key=str.casefold),
        initial_runtime_opens=[p for p in opened if os.path.isabs(p) and Path(p).is_relative_to(Path(_RUNTIME))],
        startup_tcb_authenticated=False,loaded_python_graph_attested=False,native_behavior_verified=False)


def verify_startup_profile(plan):
    reference=plan['startup_profile']; require(reference is not None and plan['case'] !='discovery','independent startup discovery required')
    path=ROOT/'results/tables/staged_rts24_saved_fresh_runtime_stk_v1_non_authoritative/startup_profile.json'
    require(reference['path']==str(path),'fixed startup profile location')
    raw=read_file(path,reference['pin']); expected=decode(raw)
    actual=startup_profile(plan)
    require(canonical(actual)==canonical(expected),'conditional TCB profile mismatch; local lease refused')
    return reference['pin']


def capture_bindings():
    namespace=globals(); rows=[]
    for name,value in tuple(namespace.items()):
        if type(value) is FunctionType and value.__module__==__name__:
            rows.append((namespace,name,value,value.__code__,value.__defaults__,value.__kwdefaults__,value.__closure__))
    for cls in (_Resource,_LocalInputs,LocalPreEntryLease,LocalPreEntryInputs,LocalRuntimeInputs):
        for name,value in vars(cls).items():
            if name in ('__new__','__init_subclass__') and type(value) in (staticmethod,classmethod):
                require(type(value) in (staticmethod,classmethod) and type(value.__func__) is FunctionType,'exact constructor descriptor required')
                rows.append((cls,name,value,None,None,None,None))
                fn=value.__func__;rows.append((value,'__func__',fn,fn.__code__,fn.__defaults__,fn.__kwdefaults__,fn.__closure__))
            elif type(value) is FunctionType: rows.append((cls,name,value,value.__code__,value.__defaults__,value.__kwdefaults__,value.__closure__))
    for name in ('_Resource','_LocalInputs','LocalPreEntryLease','LocalPreEntryInputs','LocalRuntimeInputs','ROOT','EXE','ENTRY','SOURCE_SHA','TCB_PATHS','STARTUP_ABSENT','C','W','Path','sha256','json','os','sys','get_ident','FunctionType','CodeType'):
        rows.append((namespace,name,namespace[name],None,None,None,None))
    for module,names in ((builtins,('open','compile','len','type','dict','tuple','list','object','getattr','id','vars','staticmethod','all','any')),
        (sys,('audit','addaudithook','modules','meta_path','path_hooks','path_importer_cache','_current_frames')),
        (os,('getpid','fstat','getcwd','environ')),
        (C,('WinDLL','byref','set_last_error','get_last_error','WinError','create_unicode_buffer','sizeof','POINTER')),
        (W,('DWORD','HANDLE','FILETIME','BOOL'))):
        for name in names: rows.append((module,name,getattr(module,name),None,None,None,None))
    return tuple(rows)


def check_bindings(rows,_get=getattr,_typ=type,_error=ValueError,_vars=vars):
    for namespace,name,fn,code,defaults,kw,closure in rows:
        current=namespace.get(name) if _typ(namespace) is dict else _vars(namespace).get(name) if _typ(namespace) is type else _get(namespace,name)
        if current is not fn: raise _error('pre-entry binding changed')
        if code is not None and not (fn.__code__ is code and fn.__defaults__ is defaults and fn.__kwdefaults__ is kw and fn.__closure__ is closure):
            raise _error('pre-entry callable changed')


def check_compiled_namespace(raw):
    unit=compile(raw,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0)
    classes={'_Resource','_LocalInputs','LocalPreEntryLease','LocalPreEntryInputs','LocalPreEntryUnresolved','LocalPreEntryConstructionFailed','LocalRuntimeInputs','LocalRuntimeUnresolved'}
    def check(fn,expected,cls=None):
        require(type(fn) is FunctionType and fn.__globals__ is globals() and fn.__code__==expected,'compiled bootstrap binding differs')
        if expected.co_name=='check_bindings': require(fn.__defaults__==(builtins.getattr,builtins.type,builtins.ValueError,builtins.vars),'bootstrap verifier defaults differ')
        elif expected.co_name=='seal_image': require(fn.__defaults__==(builtins.id,sha256),'bootstrap seal defaults differ')
        elif expected.co_name=='runtime_seal':require(fn.__defaults__==(None,builtins.id,sha256,builtins.tuple),'runtime seal defaults differ')
        elif expected.co_qualname=='LocalRuntimeInputs.entry':require(fn.__defaults__==(runtime_seal.__code__,FunctionType,globals(),runtime_seal.__defaults__,check_bindings.__code__,check_bindings.__defaults__,ValueError),'runtime entry defaults differ')
        elif expected.co_qualname=='LocalRuntimeInputs.close':require(fn.__defaults__==(None,FunctionType,BaseException,LocalRuntimeUnresolved,builtins.object.__setattr__,builtins.id,ValueError),'runtime close defaults differ')
        elif expected.co_qualname=='_LocalInputs.entry': require(fn.__defaults__==(builtins.id,builtins.type,sha256,builtins.ValueError),'bootstrap entry defaults differ')
        elif expected.co_qualname=='_LocalInputs.close': require(fn.__defaults__==(builtins.id,builtins.ValueError),'bootstrap cleanup defaults differ')
        elif expected.co_qualname in ('_LocalInputs.source_bytes','LocalPreEntryLease.transfer'):
            require(fn.__defaults__==(seal_image.__code__,FunctionType,globals(),seal_image.__defaults__,ValueError),'bootstrap sealed-dispatch defaults differ')
        elif expected.co_name=='namespace_failure_owner':
            require(fn.__defaults__==(builtins.vars,builtins.type,builtins.isinstance,type(sys)),'partial helper owner defaults differ')
        elif expected.co_name=='_probe_main':
            require(fn.__defaults__==(builtins.compile,builtins.exec,builtins.type,builtins.vars,tuple(vars(builtins).items())),'held probe native defaults differ')
        else: require(fn.__defaults__ is None or type(fn.__defaults__) is tuple and fn.__defaults__==(None,), 'bootstrap defaults differ')
        require(fn.__kwdefaults__ is None or fn.__kwdefaults__=={'links':False},'bootstrap keyword defaults differ')
        if expected.co_freevars==('__class__',):
            require(fn.__closure__ is not None and len(fn.__closure__)==1 and fn.__closure__[0].cell_contents is cls,'bootstrap class closure differs')
        else: require(fn.__closure__ is None,'bootstrap closure differs')
    for expected in unit.co_consts:
        if type(expected) is not CodeType or expected.co_name.startswith('<'): continue
        if expected.co_name in classes:
            cls=globals().get(expected.co_name); require(type(cls) is type and cls.__module__==__name__,'bootstrap class provenance')
            for method in expected.co_consts:
                if type(method) is CodeType and not method.co_name.startswith('<'):
                    member=vars(cls).get(method.co_name)
                    if method.co_name in ('__new__','__init_subclass__') and type(member) in (builtins.staticmethod,builtins.classmethod):
                        require(type(member) in (builtins.staticmethod,builtins.classmethod),'exact constructor descriptor required');member=member.__func__
                    check(member,method,cls)
        else: check(globals().get(expected.co_name),expected)
    require(LocalPreEntryLease.__bases__==LocalPreEntryInputs.__bases__==(_LocalInputs,) and _LocalInputs.__bases__==_Resource.__bases__==(object,), 'bootstrap class bases differ')
    require(SOURCE_SHA=='acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'
        and str(ROOT)=='D:\\CUHKSZ\\Research Project\\electricity-grid' and EXE==Path('D:/Miniconda3/envs/compute/python.exe'),'bootstrap fixed constants differ')


def seal_image(owner,_id=id,_sha=sha256):
    return (_id(owner._resource),_id(owner._ownership),_id(owner._entry_spec),_id(owner._sources),_id(owner._bindings),
        _id(owner._control),_sha(owner._raw).digest(),owner._phase,owner._resource.creator,_id(owner._exact_type),_id(owner._target_type),
        _id(owner._verifier),_id(owner._verifier_code),_id(owner._verifier_defaults),_id(owner._type),_id(owner._allocate),_id(owner._error),_id(owner._runtime_target_type),_id(owner._successor))


class _LocalInputs:
    def __new__(cls,*args,**kwargs): raise TypeError('local pre-entry inputs require the creating bootstrap')
    def _image(self):
        return (id(self._resource),id(self._ownership),id(self._entry_spec),id(self._sources),id(self._bindings),id(self._control),pin(self._raw),self._phase,self._resource.creator,id(self._exact_type),id(self._target_type))
    def entry(self,_id=id,_type=type,_sha=sha256,_reject=ValueError):
        actual=(_id(self._resource),_id(self._ownership),_id(self._entry_spec),_id(self._sources),_id(self._bindings),
            _id(self._control),_sha(self._raw).digest(),self._phase,self._resource.creator,_id(self._exact_type),_id(self._target_type),
            _id(self._verifier),_id(self._verifier_code),_id(self._verifier_defaults),_id(self._type),_id(self._allocate),_id(self._error),_id(self._runtime_target_type),_id(self._successor))
        if actual!=self._seal: raise _reject('local immutable control fields changed')
        verifier=self._verifier
        if verifier.__code__ is not self._verifier_code or verifier.__defaults__ is not self._verifier_defaults: raise self._error('held verifier changed')
        verifier(self._bindings)
        if self._type(self) is not self._exact_type: raise self._error('exact local input type required')
        require(self._resource.owner is self and self._phase=='LIVE' and self._resource.phase=='LIVE','live local input owner required')
        require(self._commit==pin(canonical(self._image())) and control_image()==self._control,'local input/control image changed')
        require(self._resource.snapshot()==self._resource.observation,'self kernel bookend differs')
        require(not self._resource.guard['faults'],'sticky pre-entry audit failure')
        require(self._resource._early is None or not self._resource._early['blocked'],'sticky early audit failure')
        plan=decode(self._raw)
        for path in plan['startup_absent']: require(not os.path.lexists(path),'startup-sensitive path appeared')
        for name,raw in self._sources: require(read_file(ROOT/name,plan['source_pins'][name])==raw,'source bytes changed')
        return self
    def source_bytes(self,name,_code=seal_image.__code__,_fn=FunctionType,_ctx=globals(),_defs=seal_image.__defaults__,_reject=ValueError):
        if _fn(_code,_ctx,'fixed_control_seal',_defs)(self)!=self._seal: raise _reject('local immutable control fields changed')
        self._entry_spec[0](self._entry_spec[1],self._entry_spec[2],'held_entry',self._entry_spec[3])(self)
        require(name in dict(self._sources),'held source name required'); return dict(self._sources)[name]
    def close(self,_id=id,_reject=ValueError):
        resource=self._resource
        if self._cleanup_seal!=(_id(resource),_id(self._ownership),_id(self._ownership[2]),_id(self._ownership[3]),_id(self._ownership[4]),resource.creator):
            raise LocalPreEntryUnresolved(self,_reject('local cleanup ownership changed'),())
        require(self._ownership[0] is resource and self._ownership[1]==resource.creator,'original local ownership required')
        cleanup=self._ownership[3](self._ownership[2],{'BaseException':self._ownership[4],'__builtins__':{}},'held_native_cleanup',(None,))
        if resource.owner is not self:
            successor=self._successor
            require(self._phase=='CONSUMED' and successor is not None and successor._resource is resource,'foreign resource owner')
            if resource.owner is not successor:
                require(type(self) is LocalPreEntryLease and type(successor) is LocalPreEntryInputs and successor._phase=='CONSUMED'
                    and successor._successor is resource.owner and type(resource.owner) is LocalRuntimeInputs
                    and resource.owner._source is successor,'runtime descendant owner differs')
            elif type(resource.owner) is LocalRuntimeInputs:require(resource.owner._source is self,'runtime successor source differs')
            return
        if self._phase=='CLOSED': return
        if self._phase=='UNRESOLVED':
            if resource.phase!='LIVE': raise self._failure
            primary=self._failure
            cleanup(resource,self,primary); self._phase='CLOSED'
            raise LocalPreEntryUnresolved(self,primary,()) from primary
        primary=None
        try: self._entry_spec[0](self._entry_spec[1],self._entry_spec[2],'held_entry',self._entry_spec[3])(self)
        except BaseException as error: primary=error
        try: cleanup(resource,self,primary)
        except BaseException as error:
            self._phase='UNRESOLVED'; self._failure=error; raise
        self._phase='CLOSED'
        if primary is not None: raise LocalPreEntryUnresolved(self,primary,()) from primary
    def __reduce__(self): raise TypeError('local inputs and self HANDLEs cannot be serialized')
    def __copy__(self): raise TypeError('local inputs cannot be copied')
    def __deepcopy__(self,memo): raise TypeError('local inputs cannot be copied')


class LocalPreEntryInputs(_LocalInputs):
    """Actual same-process owner, not an external role or runtime capability."""
    def transfer_runtime(self,namespace,namespace_specs):
        self.entry();resource=self._resource
        require(not resource.guard['runtime_attempted'],'single runtime handoff attempt required');resource.guard['runtime_attempted']=True
        require(type(namespace_specs) is tuple and len(namespace_specs)==3,'closed namespace runtime plans required')
        plan=check_plan(self._raw);ref=plan['namespace_helper'];raw=read_file(ref['path'],ref['pin'])
        compiled=compile(raw,ref['path'],'exec',dont_inherit=True,optimize=0)
        expected={c.co_name:c for c in compiled.co_consts if type(c) is CodeType}
        for spec,name in zip(namespace_specs,('prepare_runtime_namespace','verify_runtime_namespace','close_runtime_namespace')):
            require(type(spec) is tuple and len(spec)==4 and spec[0] is FunctionType and type(spec[1]) is CodeType
                and spec[1]==expected[name] and type(spec[2]) is dict,'held namespace runtime code required')
            fn=spec[2].get(name)
            require(type(fn) is FunctionType and fn.__code__ is spec[1] and fn.__globals__ is spec[2]
                and fn.__defaults__ is spec[3] and fn.__closure__ is None,'original namespace runtime function required')
        context=namespace_specs[0][2]
        require(all(spec[2] is context for spec in namespace_specs),'single namespace helper context required')
        require(type(namespace) is context.get('LiveEntryNamespace') and namespace._inputs is self and namespace._phase=='LIVE'
            and namespace._runtime_peer is None and namespace._creator==(os.getpid(),get_ident()),'original namespace producer required')
        target=object.__new__(self._runtime_target_type)
        for name,value in dict(_source=self,_namespace=namespace,_resource=resource,_ownership=self._ownership,
            _cleanup_seal=self._cleanup_seal,_sources=self._sources,_raw=self._raw,_bindings=self._bindings,
            _pre_control=self._control,_creator=resource.creator,_namespace_specs=namespace_specs,
            _phase='PREPARING',_failure=None,_cleanup_started=False,_boundary=None,_boundary_entry=None,
            _boundary_finish=None,_boundary_phase=None,_boundary_profile=None,_boundary_pending=None,_boundary_bindings=None,_adapter=None,_adapter_bindings=(),_retention=(),
            _control_after_import=None,_audit_handed_off=False,_source_bookends=0,_import_profile_matched=False).items():object.__setattr__(target,name,value)
        try:
            spec=namespace_specs[0];snapshot=spec[0](spec[1],spec[2],'held_namespace_prepare',spec[3])(namespace,target)
            require(type(snapshot) is tuple,'immutable namespace runtime snapshot required');object.__setattr__(target,'_namespace_snapshot',snapshot)
            object.__setattr__(target,'_seal',runtime_seal(target,'ADOPTED'))
            sys.audit('electricity_grid.runtime.transfer_prepared',self,namespace,target)
            self._entry_spec[0](self._entry_spec[1],self._entry_spec[2],'held_last_input_bookend',self._entry_spec[3])(self)
            final_snapshot=spec[0](spec[1],spec[2],'held_last_namespace_bookend',spec[3])(namespace,target)
            require(final_snapshot==snapshot and target._phase=='PREPARING' and runtime_seal(target,'ADOPTED')==target._seal,
                'prepared runtime changed before ownership commitment')
            object.__setattr__(resource,'owner',target)  # Unique native ownership commitment.
            object.__setattr__(self,'_successor',target);object.__setattr__(self,'_phase','CONSUMED')
            object.__setattr__(namespace,'_runtime_peer',target);object.__setattr__(namespace,'_phase','CONSUMED')
            object.__setattr__(target,'_phase','ADOPTED')
            sys.audit('electricity_grid.runtime.owner_committed',target)
            return target.entry()
        except BaseException as primary:
            if resource.owner is self:
                object.__setattr__(target,'_phase','ABORTED');raise
            self._phase='CONSUMED';self._successor=target
            object.__setattr__(namespace,'_runtime_peer',target);object.__setattr__(namespace,'_phase','CONSUMED')
            object.__setattr__(target,'_phase','UNRESOLVED');object.__setattr__(target,'_failure',LocalRuntimeUnresolved(target,primary,()))
            raise target._failure from primary


class LocalRuntimeUnresolved(RuntimeError):
    def __init__(self,owner,primary,secondary):
        self.owner,self.primary,self.secondary=owner,primary,tuple(secondary)
        super().__init__('local runtime ownership or import unresolved')
    def __reduce__(self):raise TypeError('runtime failure retains local owner')


def runtime_seal(owner,phase=None,_id=id,_sha=sha256,_tuple=tuple):
    return _tuple(_id(value) for value in (owner._source,owner._namespace,owner._resource,owner._ownership,owner._sources,
        owner._cleanup_seal,owner._bindings,owner._pre_control,owner._namespace_specs,owner._namespace_snapshot,owner._boundary,
        owner._boundary_entry,owner._boundary_finish,owner._boundary_phase,owner._boundary_profile,owner._boundary_pending,owner._boundary_bindings,owner._adapter,owner._adapter_bindings,owner._retention,
        owner._control_after_import))+(_sha(owner._raw).digest(),owner._creator,owner._phase if phase is None else phase,
        owner._audit_handed_off,owner._import_profile_matched)


class LocalRuntimeInputs:
    """Exact native owner for one namespace/import episode; never role authority."""
    __slots__=('_source','_namespace','_resource','_ownership','_cleanup_seal','_sources','_raw','_bindings','_pre_control','_creator','_namespace_specs',
        '_phase','_failure','_cleanup_started','_boundary','_boundary_entry','_boundary_finish','_boundary_phase','_boundary_profile','_boundary_pending','_boundary_bindings',
        '_adapter','_adapter_bindings','_retention','_control_after_import','_audit_handed_off','_source_bookends','_import_profile_matched','_namespace_snapshot','_seal')
    def __new__(cls,*args,**kwargs):raise TypeError('runtime requires original input handoff')
    def __setattr__(self,name,value):raise AttributeError('runtime ownership fields are frozen')
    def __delattr__(self,name):raise AttributeError('runtime ownership fields are frozen')
    def __init_subclass__(cls,**kwargs):raise TypeError('runtime input subclasses are closed')
    def entry(self,_code=runtime_seal.__code__,_fn=FunctionType,_ctx=globals(),_defs=runtime_seal.__defaults__,
            _check=check_bindings.__code__,_check_defs=check_bindings.__defaults__,_reject=ValueError):
        if _fn(_code,_ctx,'held_runtime_seal',_defs)(self)!=self._seal:raise _reject('runtime immutable state differs')
        _fn(_check,_ctx,'held_runtime_roots',_check_defs)(self._bindings)
        require(type(self) is LocalRuntimeInputs and self._phase in ('ADOPTED','IMPORTING','OBSERVED','LIVE'),'active exact runtime required')
        require(self._resource.owner is self and self._resource.phase=='LIVE' and self._source._phase=='CONSUMED'
            and self._source._successor is self and self._source._resource is self._resource,'exact runtime native owner required')
        require(self._resource.snapshot()==self._resource.observation,'runtime self kernel bookend differs')
        require(not self._resource.guard['faults'] and not self._resource._early['blocked'],'sticky pre-entry fault prevents runtime')
        spec=self._namespace_specs[1];spec[0](spec[1],spec[2],'held_runtime_namespace',spec[3])(self._namespace,self)
        if self._boundary_bindings is not None:
            factory,code,context,defaults,expected=self._boundary_bindings;factory(code,context,'held_B_S_expected_roots',defaults)(expected)
        if self._boundary is None:require(control_image()==self._pre_control,'runtime pre-import control differs')
        else:
            spec=self._boundary_entry;spec[0](spec[1],spec[2],'held_import_boundary_entry',spec[3])(self._boundary)
        if self._phase in ('OBSERVED','LIVE'):
            require(self._boundary is not None and self._adapter is not None and self._audit_handed_off
                and control_image()==self._control_after_import,'runtime post-import control differs')
            spec=self._boundary_phase;require(spec[0](spec[1],spec[2],'held_closed_boundary_phase',spec[3])(self._boundary)=='CLOSED','runtime needs completed import boundary')
            require(self._import_profile_matched is (self._phase=='LIVE'),'runtime profile/phase differs')
        if self._adapter is not None:
            require(sys.modules.get('src.staged_rts24_saved_fresh_adoption_v1') is self._adapter,'runtime adapter module changed')
            namespace=vars(self._adapter)
            for name,fn,code,defaults,kw,closure in self._adapter_bindings:
                require(namespace.get(name) is fn and fn.__code__ is code and fn.__defaults__ is defaults
                    and canonical(fn.__kwdefaults__)==kw and fn.__closure__ is closure and fn.__globals__ is namespace,'runtime adapter callable changed')
            require(self._adapter_bindings and self._retention,'complete nonempty runtime import proof required')
            require(all(name in sys.modules and sys.modules[name] is module for name,module in self._retention),'runtime retained module changed')
        return self
    def source_bookend(self):
        plan=check_plan(self._raw)
        for name,raw in self._sources:require(read_file(ROOT/name,plan['source_pins'][name])==raw,'runtime held source changed')
        object.__setattr__(self,'_source_bookends',self._source_bookends+1)
        return plan['source_pins']
    def source_bytes(self,name):
        self.entry();self.source_bookend();require(name in dict(self._sources),'runtime held source required');return dict(self._sources)[name]
    def prepare_boundary(self,entry_spec,finish_spec,phase_spec,profile_spec,pending_spec,expected_bindings):
        self.entry();require(self._phase=='ADOPTED' and self._boundary is None and self._boundary_entry is None,'single runtime import boundary required')
        plan=check_plan(self._raw);ref=plan['import_helper'];raw=read_file(ref['path'],ref['pin'])
        compiled=compile(raw,ref['path'],'exec',dont_inherit=True,optimize=0)
        cls=next(c for c in compiled.co_consts if type(c) is CodeType and c.co_name=='BootstrapImportBoundary')
        expected={c.co_name:c for c in cls.co_consts if type(c) is CodeType}
        context=entry_spec[2]
        require(context.get('_READ_FILE') is read_file and read_file.__globals__ is globals(),'exact core import reader required')
        for spec,name in zip((entry_spec,finish_spec,phase_spec,profile_spec,pending_spec),('_entry','close','phase','profile_raw','claim_pending')):
            require(type(spec) is tuple and len(spec)==4 and spec[0] is FunctionType and type(spec[1]) is CodeType and type(spec[2]) is dict,'held boundary methods required')
            require(spec[2] is context,'single boundary helper context required')
            boundary_type=spec[2].get('BootstrapImportBoundary');require(type(boundary_type) is type,'exact boundary class required')
            fn=vars(boundary_type).get(name)
            require(spec[1]==expected[name]
                and type(fn) is FunctionType and fn.__code__ is spec[1] and fn.__globals__ is spec[2]
                and fn.__defaults__ is spec[3] and fn.__closure__ is None,'original boundary source method required')
        verifier=context.get('verify_bootstrap_import_bindings')
        expected_code=next(c for c in compiled.co_consts if type(c) is CodeType and c.co_name=='verify_bootstrap_import_bindings')
        require(type(verifier) is FunctionType and verifier.__globals__ is context and verifier.__code__==expected_code
            and verifier.__defaults__==(builtins.type,builtins.vars,builtins.ValueError,builtins.tuple,builtins.sorted),'original B_S expected-root verifier required')
        require(type(expected_bindings) is tuple and expected_bindings,'bootstrap-held B_S expected bindings required')
        proof=(FunctionType,verifier.__code__,context,verifier.__defaults__,expected_bindings)
        proof[0](proof[1],proof[2],'held_initial_B_S_roots',proof[3])(proof[4])
        object.__setattr__(self,'_boundary_bindings',proof)
        object.__setattr__(self,'_boundary_entry',entry_spec);object.__setattr__(self,'_boundary_finish',finish_spec)
        object.__setattr__(self,'_boundary_phase',phase_spec);object.__setattr__(self,'_boundary_profile',profile_spec)
        object.__setattr__(self,'_boundary_pending',pending_spec);object.__setattr__(self,'_seal',runtime_seal(self))
        return self
    def own_pending_boundary(self,boundary):
        self.entry()
        require(self._phase=='ADOPTED' and self._boundary is None and self._boundary_entry is not None,'prepared single boundary required')
        require(type(boundary) is self._boundary_entry[2].get('BootstrapImportBoundary') and boundary._creator==self._creator[:2],'original pending import boundary required')
        require(self._boundary_entry[2].get('_READ_FILE') is read_file and read_file.__globals__ is globals(),'exact pending import reader required')
        ref=check_plan(self._raw)['import_policy'];require(boundary._profile_raw==read_file(ref['path'],ref['pin']),'pinned pending policy required')
        spec=self._boundary_pending;spec[0](spec[1],spec[2],'held_pending_boundary_claim',spec[3])(boundary,self)
        object.__setattr__(self,'_boundary',boundary);object.__setattr__(self,'_phase','IMPORTING');object.__setattr__(self,'_seal',runtime_seal(self))
        return self
    def activate_boundary(self):
        self.entry();spec=self._boundary_phase
        require(spec[0](spec[1],spec[2],'held_active_boundary_phase',spec[3])(self._boundary)=='ACTIVE_B3','new import sentinel must be active')
        return self
    def handoff_audit(self):
        self.entry();require(not self._audit_handed_off and self._boundary is not None,'single runtime audit handoff required')
        spec=self._boundary_phase;require(spec[0](spec[1],spec[2],'held_boundary_phase',spec[3])(self._boundary)=='ACTIVE_B3','active B_S guard required')
        old=self._resource.guard;early=self._resource._early
        require(old['active'] and early['active'],'both predecessor hooks must be active')
        sys.audit('electricity_grid.runtime.audit_handoff_prepared',self)
        old['active']=False
        sys.audit('electricity_grid.runtime.audit_handoff_between',self,self._boundary._owner[2])
        require(self._boundary._handoff_seen==1,'new B_S hook did not observe audit handoff')
        self.entry()
        early['active']=False
        object.__setattr__(self,'_audit_handed_off',True);object.__setattr__(self,'_seal',runtime_seal(self))
        sys.audit('electricity_grid.runtime.audit_handoff_complete',self)
        return self.entry()
    def finish_import(self,adapter,adapter_bindings,retention):
        self.entry();require(self._phase=='IMPORTING' and self._audit_handed_off,'runtime import handoff incomplete')
        spec=self._boundary_phase;require(spec[0](spec[1],spec[2],'held_boundary_final_phase',spec[3])(self._boundary)=='CLOSED','closed B_S import required')
        require(adapter is self._boundary._adapter and type(adapter_bindings) is tuple and type(retention) is tuple
            and adapter_bindings is self._boundary._runtime_bindings and retention is self._boundary._retention
            and adapter_bindings and retention,'boundary-held complete import proof required')
        self.source_bookend()
        spec=self._boundary_profile;observed=spec[0](spec[1],spec[2],'held_B_S_profile',spec[3])(self._boundary)
        ref=check_plan(self._raw)['import_profile'];profile_matched=ref is not None
        if ref is not None:require(read_file(ref['path'],ref['pin'])==observed,'independent B_S profile differs')
        object.__setattr__(self,'_adapter',adapter);object.__setattr__(self,'_adapter_bindings',adapter_bindings);object.__setattr__(self,'_retention',retention)
        object.__setattr__(self,'_control_after_import',control_image());object.__setattr__(self,'_import_profile_matched',profile_matched)
        object.__setattr__(self,'_phase','LIVE' if profile_matched else 'OBSERVED');object.__setattr__(self,'_seal',runtime_seal(self))
        return self.entry()
    def close(self,primary=None,_fn=FunctionType,_base=BaseException,_failure=LocalRuntimeUnresolved,_put=object.__setattr__,_id=id,_reject=ValueError):
        if self._cleanup_started:
            if self._failure is not None:raise self._failure
            if self._phase!='CLOSED':raise _failure(self,_reject('incomplete prior runtime cleanup'),())
            return
        _put(self,'_cleanup_started',True);errors=[]
        if primary is None and self._failure is not None:primary=self._failure
        try:
            if self._phase in ('ADOPTED','IMPORTING','OBSERVED','LIVE'):
                try:self.entry();self.source_bookend()
                except _base as error:
                    if primary is None:primary=error
                    else:errors.append(('runtime_bookend',error))
            if self._boundary is not None:
                try:
                    spec=self._boundary_finish;spec[0](spec[1],spec[2],'held_boundary_close',spec[3])(self._boundary,primary)
                except _base as error:errors.append(('import_boundary',error))
            try:
                spec=self._namespace_specs[2];spec[0](spec[1],spec[2],'held_runtime_namespace_close',spec[3])(self._namespace,self)
            except _base as error:errors.append(('namespace',error))
        except _base as error:errors.append(('cleanup_control',error))
        try:
            resource=self._resource;ownership=self._ownership
            if self._cleanup_seal!=(_id(resource),_id(ownership),_id(ownership[2]),_id(ownership[3]),_id(ownership[4]),resource.creator):
                raise _reject('runtime cleanup ownership changed')
            cleanup=_fn(ownership[2],{'BaseException':ownership[4],'__builtins__':{}},'held_runtime_native_cleanup',(None,))
            cleanup(resource,self,primary)
        except _base as error:errors.append(('native',error))
        try:
            self._resource.guard['active']=False
            if self._resource._early is not None:self._resource._early['active']=False
        except _base as error:errors.append(('old_hook_deactivation',error))
        try:
            if any(self._resource.pending):errors.append(('pending_handles',_reject('native cleanup incomplete')))
        except _base as error:errors.append(('pending_observation',error))
        if primary is not None or errors:
            _put(self,'_phase','UNRESOLVED');_put(self,'_failure',_failure(self,primary,errors));raise self._failure from primary
        _put(self,'_phase','CLOSED')
    def __reduce__(self):raise TypeError('runtime inputs cannot be serialized')
    def __copy__(self):raise TypeError('runtime inputs cannot be copied')
    def __deepcopy__(self,memo):raise TypeError('runtime inputs cannot be copied')


class LocalPreEntryLease(_LocalInputs):
    def transfer(self,_code=seal_image.__code__,_fn=FunctionType,_ctx=globals(),_defs=seal_image.__defaults__,_reject=ValueError):
        if _fn(_code,_ctx,'fixed_control_seal',_defs)(self)!=self._seal: raise _reject('local immutable control fields changed')
        self._entry_spec[0](self._entry_spec[1],self._entry_spec[2],'held_entry',self._entry_spec[3])(self)
        target=self._allocate(self._target_type); resource=self._resource
        for name,value in self.__dict__.items(): object.__setattr__(target,name,value)
        target._phase='PREPARING'
        try:
            sys.audit('electricity_grid.pre_entry.transfer_prepared',self,target)
            resource.owner=target  # Sole ownership commitment point.
            self._phase='CONSUMED'; self._successor=target; target._phase='LIVE'; target._exact_type=self._target_type; target._commit=pin(canonical(target._image()));target._seal=seal_image(target)
            resource.guard['events'].append('transfer_committed')
            return target._entry_spec[0](target._entry_spec[1],target._entry_spec[2],'held_entry',target._entry_spec[3])(target)
        except BaseException as error:
            if resource.owner is self:
                target._phase='ABORTED'; raise
            self._phase='CONSUMED'; target._phase='UNRESOLVED'; target._failure=LocalPreEntryUnresolved(target,error,())
            raise target._failure from error


def install_guard(plan):
    paths={os.path.normcase(str(ROOT/n)) for n in plan['source_pins']}
    protected=(str(ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'),str(ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative'))
    state=dict(active=True,self_live=False,events=['manifest_received'],source_open_attempts=0,blocked_source_opens=0,
        protected_open_attempts=0,write_attempts=0,process_attempts=0,runtime_attempted=False,faults=[],sentinel=0)
    token=object()
    def reject(kind): state['faults'].append(kind); raise ValueError('pre-entry audit rejected '+kind)
    def audit(event,args):
        if not state['active']: return
        if event in ('object.__setattr__','object.__delattr__') and len(args)>=2 and type(args[0]) is FunctionType and args[1] in ('__code__','__defaults__','__kwdefaults__'): reject('function_metadata_mutation')
        if event=='electricity_grid.pre_entry.install':
            if len(args)!=1 or args[0] is not token or state['sentinel']: reject('sentinel')
            state['sentinel']=1; return
        if event=='open':
            name,mode,flags=args[:3]
            if type(mode) is str and any(c in mode for c in 'wax+') or type(flags) is int and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_APPEND|os.O_TRUNC):
                state['write_attempts']+=1; reject('write')
            if isinstance(name,(str,bytes,os.PathLike)):
                path=os.path.normcase(os.path.abspath(os.fsdecode(name)))
                if path in paths:
                    state['source_open_attempts']+=1
                    if not state['self_live']: state['blocked_source_opens']+=1; reject('source_before_self')
                if any(path==os.path.normcase(p) or path.startswith(os.path.normcase(p)+os.sep) for p in protected):
                    state['protected_open_attempts']+=1; reject('protected_input')
        if event in ('subprocess.Popen','os.system','os.posix_spawn') or event.startswith(('os.spawn','os.exec')):
            state['process_attempts']+=1; reject('process')
        if event in ('os.remove','os.rmdir','os.rename','os.mkdir','os.link','os.symlink','os.chmod','os.truncate','os.utime'): reject('mutation')
    sys.addaudithook(audit); sys.audit('electricity_grid.pre_entry.install',token)
    require(state['sentinel']==1,'pre-entry audit installation absent'); state['callback']=audit
    return state


def open_local_pre_entry_lease(plan_raw,guard):
    global _ATTEMPTED
    require(__name__=='__main__' and _RELEASED and _ATTEMPTED is False,'single creating pre-entry bootstrap required'); _ATTEMPTED=True
    plan=check_plan(plan_raw)
    require(canonical(dict(os.environ))==canonical(plan['environment']) and os.getcwd()==plan['cwd'],'actual startup environment/cwd differs')
    require(tuple(sys.path)==tuple(plan['initial_paths']) and set(sys._current_frames())=={get_ident()},'single cold bootstrap path/thread required')
    require(not any(n==p or n.startswith(p+'.') for n in sys.modules for p in ('src','experiments','tests','numpy','scipy','pyomo','highspy','site','sitecustomize','usercustomize')),'pre-entry module set differs')
    require(tuple((v.__module__,v.__name__) for v in sys.meta_path)==(('_frozen_importlib','BuiltinImporter'),('_frozen_importlib','FrozenImporter'),('_frozen_importlib_external','PathFinder')),'fixed no-site import baseline required')
    require(len(sys.orig_argv)==10 and sys.orig_argv[1:6]==['-P','-B','-s','-S','-c'],'exact bootstrap argv required')
    code_raw=sys.orig_argv[6].encode('utf-8')
    require(pin(code_raw)==plan['bootstrap_pin'] and _MODULE_CODE==compile(code_raw,'<string>','exec',dont_inherit=True,optimize=0),'actual bootstrap code differs')
    require(sys.argv==['-c',*sys.orig_argv[7:]] and pin(plan_raw)['sha256']==sys.argv[3],'released manifest/argv differs')
    require(_PAYLOAD_CODE==compile(_PAYLOAD_RAW,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0),'loaded bootstrap payload differs')
    check_compiled_namespace(_PAYLOAD_RAW)
    matched_profile=verify_startup_profile(plan)
    owner=object.__new__(LocalPreEntryLease); resource=None
    try:
        resource=_Resource(owner,guard); owner._resource=resource
        owner._ownership=(resource,resource.creator,resource.cleanup_code,FunctionType,BaseException); owner._phase='OPENING'
        owner._cleanup_seal=(id(resource),id(owner._ownership),id(owner._ownership[2]),id(owner._ownership[3]),id(owner._ownership[4]),resource.creator)
        resource.open()
        require(Path(resource.observation['image_path']).absolute()==EXE.absolute(),'kernel executable differs')
        require(resource.observation['command_line_sha']==pin(subprocess.list2cmdline(sys.orig_argv).encode('utf-8')),'OS command line differs')
        read_file(EXE,plan['executable_pin'],links=True)
        for path,expected in plan['selected_runtime_file_observations'].items(): read_file(path,expected,links=True)
        for path in plan['startup_absent']: require(not os.path.lexists(path),'startup-sensitive path appeared')
        guard['events'].append('source_read_begin')
        require(sum(p['bytes'] for p in plan['source_pins'].values())<=2*1024**2,'Source49 aggregate cap')
        sources=tuple((name,read_file(ROOT/name,expected)) for name,expected in sorted(plan['source_pins'].items()))
        owner._raw=plan_raw; owner._sources=sources; owner._control=control_image(); owner._bindings=capture_bindings()
        owner._matched_startup_profile=matched_profile
        owner._verifier=check_bindings; owner._verifier_code=check_bindings.__code__; owner._verifier_defaults=check_bindings.__defaults__
        owner._entry_spec=(FunctionType,_LocalInputs.entry.__code__,globals(),_LocalInputs.entry.__defaults__); owner._exact_type=LocalPreEntryLease; owner._target_type=LocalPreEntryInputs
        owner._type=type; owner._allocate=object.__new__; owner._error=ValueError
        owner._phase='LIVE'; owner._failure=None; owner._successor=None; owner._runtime_target_type=LocalRuntimeInputs; owner._commit=pin(canonical(owner._image()))
        owner._seal=seal_image(owner)
        return owner._entry_spec[0](owner._entry_spec[1],owner._entry_spec[2],'held_entry',owner._entry_spec[3])(owner)
    except BaseException as primary:
        if resource is not None:
            cleanup=owner._ownership[3](owner._ownership[2],{'BaseException':owner._ownership[4],'__builtins__':{}},'held_native_cleanup',(None,))
            try: cleanup(resource,owner,primary); owner._phase='CLOSED'
            except BaseException as error:
                owner._phase='UNRESOLVED'; owner._failure=error
                raise LocalPreEntryConstructionFailed(owner,primary,(error,)) from primary
            raise LocalPreEntryConstructionFailed(owner,primary,()) from primary
        raise
