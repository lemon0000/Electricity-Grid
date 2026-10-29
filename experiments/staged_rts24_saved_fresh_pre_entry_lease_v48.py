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
                profile=root+'results/tables/staged_rts24_saved_fresh_complete_bootstrap_native_v2_non_authoritative/startup_profile.json'
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
from threading import get_ident, Lock
from types import FunctionType, CodeType, SimpleNamespace

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
    fields='schema authority nonce source_pins source_epoch bootstrap_pin executable_pin python environment cwd initial_paths selected_runtime_file_observations startup_absent startup_profile namespace_helper import_helper import_policy import_profile producer_helpers graph_contract case'
    require(type(plan) is dict and set(plan)==set(fields.split()), 'closed manifest fields')
    require(plan['schema']=='staged_saved_F_complete_bootstrap_manifest_v1' and plan['authority']=='DRAFT_NONAUTHORITATIVE', 'manifest schema')
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
    require(plan['case'] in ('discovery','import_discovery','producer'), 'closed diagnostic case')
    require(type(plan['selected_runtime_file_observations']) is dict and set(plan['selected_runtime_file_observations'])==set(TCB_PATHS)
        and plan['startup_absent']==list(STARTUP_ABSENT), 'selected runtime observations')
    require(plan['startup_profile'] is None if plan['case'] =='discovery' else type(plan['startup_profile']) is dict and set(plan['startup_profile'])=={'path','pin'} and plan['startup_profile']['path']==str(ROOT/'results/tables/staged_rts24_saved_fresh_complete_bootstrap_native_v2_non_authoritative/startup_profile.json'),'two-stage startup profile')
    require(type(plan['namespace_helper']) is dict and set(plan['namespace_helper'])=={'path','pin'} and plan['namespace_helper']['path']==str(ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v4.py'),'fixed namespace helper reference')
    for field in ('import_helper','import_policy'):
        require(type(plan[field]) is dict and set(plan[field])=={'path','pin'},'fixed runtime attachment reference')
    require(plan['import_profile'] is None if plan['case'] in ('discovery','import_discovery') else type(plan['import_profile']) is dict and set(plan['import_profile'])=={'path','pin'},'two-stage B_S import profile')
    require(plan['case']!='producer' or plan['import_profile']['path']==str(ROOT/'results/tables/staged_rts24_saved_fresh_complete_bootstrap_native_v2_non_authoritative/import_profile.json'),'independent complete-bootstrap import profile required');check_producer_helpers(plan);require(canonical(plan['graph_contract'])==canonical(construction_graph_contract()),'exact graph contract required');return plan


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
        self._native_roots=capture_native_cleanup_roots(self)
    def open(self):
        verify_native_cleanup_roots(self,self._native_roots)
        process=checked_call(self.held,'OpenProcess',0x1000,False,self.creator[0])
        self.pending[0]=(process,'live')
        record_native_open(self,0,self.pending[0][0])
        sys.audit('electricity_grid.pre_entry.process_handle_opened',self)
        verify_native_cleanup_roots(self,self._native_roots)
        thread=checked_call(self.held,'OpenThread',0x0800,False,self.creator[2])
        self.pending[1]=(thread,'live')
        record_native_open(self,1,self.pending[1][0])
        self.observation=self.snapshot()
        self._native_live=(self._native_roots,((process,'live'),(thread,'live')),self.creator)
        require(tuple(self.pending)==self._native_live[1] and self.close_calls==[0,0],'original open returns changed')
        self.phase='LIVE'; self.guard['self_live']=True
        if self._early is not None: self._early['sources_allowed']=True
        self.guard['events'].append('self_handles_live')
        return self._native_live
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
    path=ROOT/'results/tables/staged_rts24_saved_fresh_complete_bootstrap_native_v2_non_authoritative/startup_profile.json'
    require(reference['path']==str(path),'fixed startup profile location')
    raw=read_file(path,reference['pin']); expected=decode(raw)
    actual=startup_profile(plan)
    require(canonical(actual)==canonical(expected),'conditional TCB profile mismatch; local lease refused')
    return reference['pin']


def capture_bindings():
    namespace=globals(); rows=[]
    rows.extend((namespace,name,None,'absent_builtin_global',None,None,None)
        for name in vars(builtins) if name not in namespace)
    for name,value in tuple(namespace.items()):
        if type(value) is FunctionType and value.__module__==__name__:
            rows.append((namespace,name,value,value.__code__,value.__defaults__,value.__kwdefaults__,value.__closure__))
    for cls in (_Resource,_LocalInputs,LocalPreEntryLease,LocalPreEntryInputs,LocalRuntimeInputs,_RuntimeCleanup,_NativeCleanupRoots):
        rows.append((cls,'__keys__',tuple(vars(cls)),'class_keys',None,None,None))
        for name,value in vars(cls).items():
            if name in ('__new__','__init_subclass__') and type(value) in (staticmethod,classmethod):
                require(type(value) in (staticmethod,classmethod) and type(value.__func__) is FunctionType,'exact constructor descriptor required')
                rows.append((cls,name,value,None,None,None,None))
                fn=value.__func__;rows.append((value,'__func__',fn,fn.__code__,fn.__defaults__,fn.__kwdefaults__,fn.__closure__))
            elif type(value) is FunctionType: rows.append((cls,name,value,value.__code__,value.__defaults__,value.__kwdefaults__,value.__closure__))
    for name in ('_Resource','_LocalInputs','LocalPreEntryLease','LocalPreEntryInputs','LocalRuntimeInputs','ROOT','EXE','ENTRY','SOURCE_SHA','TCB_PATHS','STARTUP_ABSENT','C','W','Path','sha256','json','os','sys','get_ident','FunctionType','CodeType','SimpleNamespace','Lock','_RuntimeCleanup','_NativeCleanupRoots'):
        rows.append((namespace,name,namespace[name],None,None,None,None))
    for module,names in ((builtins,('open','compile','len','type','dict','tuple','list','object','getattr','id','vars','staticmethod','all','any')),
        (sys,('audit','addaudithook','modules','meta_path','path_hooks','path_importer_cache','_current_frames')),
        (os,('getpid','fstat','getcwd','environ')),
        (C,('WinDLL','byref','set_last_error','get_last_error','WinError','create_unicode_buffer','sizeof','POINTER')),
        (W,('DWORD','HANDLE','FILETIME','BOOL'))):
        for name in names: rows.append((module,name,getattr(module,name),None,None,None,None))
    return tuple(rows)


def check_bindings(rows,_get=getattr,_typ=type,_error=ValueError,_vars=vars,_tuple=tuple):
    for namespace,name,fn,code,defaults,kw,closure in rows:
        if code=='class_keys':
            if _tuple(_vars(namespace))!=fn:raise _error('bootstrap class keys changed')
            continue
        if code=='absent_builtin_global':
            if name in namespace:raise _error('bootstrap builtin shadowing changed')
            continue
        current=namespace.get(name) if _typ(namespace) is dict else _vars(namespace).get(name) if _typ(namespace) is type else _get(namespace,name)
        if current is not fn: raise _error('pre-entry binding changed')
        if code is not None and not (fn.__code__ is code and fn.__defaults__ is defaults and fn.__kwdefaults__ is kw and fn.__closure__ is closure):
            raise _error('pre-entry callable changed')


def check_compiled_namespace(raw):
    unit=compile(raw,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0)
    classes={'_Resource','_LocalInputs','LocalPreEntryLease','LocalPreEntryInputs','LocalPreEntryUnresolved',
        'LocalPreEntryConstructionFailed','LocalRuntimeInputs','LocalRuntimeUnresolved','_NativeCleanupRoots','_RuntimeCleanup'}
    def check(fn,expected,cls=None):
        require(type(fn) is FunctionType and fn.__globals__ is globals() and fn.__code__==expected,'compiled bootstrap binding differs')
        if expected.co_name=='check_bindings': require(fn.__defaults__==(builtins.getattr,builtins.type,builtins.ValueError,builtins.vars,builtins.tuple),'bootstrap verifier defaults differ')
        elif expected.co_name=='verify_native_cleanup_roots':
            require(fn.__defaults__==(builtins.object.__getattribute__,builtins.type,builtins.tuple,builtins.ValueError,builtins.vars),'native root verifier defaults differ')
        elif expected.co_name=='cleanup_root_image':
            require(fn.__defaults__==(builtins.object.__getattribute__,builtins.id,builtins.tuple),'cleanup image defaults differ')
        elif expected.co_name=='run_runtime_cleanup':
            roots=(builtins.object.__getattribute__,builtins.object.__setattr__,builtins.type,builtins.tuple,builtins.dict,builtins.list,
                builtins.len,builtins.any,FunctionType,BaseException,ValueError,LocalRuntimeUnresolved,RuntimeError.__new__,RuntimeError.__init__,
                os.getpid,get_ident,SimpleNamespace,verify_native_cleanup_roots.__code__,verify_native_cleanup_roots.__defaults__,
                cleanup_root_image.__code__,cleanup_root_image.__defaults__,builtins.id,builtins.int,builtins.str,builtins.bool,builtins.all,
                cleanup_binding_snapshot.__code__,cleanup_binding_snapshot.__defaults__)
            require(fn.__defaults__==(None,roots),'source cleanup runner defaults differ')
        elif expected.co_name=='cleanup_binding_snapshot':
            require(fn.__defaults__==((builtins.type,builtins.list,builtins.tuple,builtins.len,ValueError,builtins.range,BaseException,builtins.int,builtins.str,builtins.bool),),'binding snapshot defaults differ')
        elif expected.co_name=='commit_cleanup_binding':
            require(fn.__defaults__==(builtins.list.append,),'binding append defaults differ')
        elif expected.co_name=='seal_image': require(fn.__defaults__==(builtins.id,sha256),'bootstrap seal defaults differ')
        elif expected.co_name=='runtime_seal':require(fn.__defaults__==(None,builtins.id,sha256,builtins.tuple),'runtime seal defaults differ')
        elif expected.co_qualname=='LocalRuntimeInputs.entry':require(fn.__defaults__==(runtime_seal.__code__,FunctionType,globals(),runtime_seal.__defaults__,check_bindings.__code__,check_bindings.__defaults__,ValueError),'runtime entry defaults differ')
        elif expected.co_qualname=='LocalRuntimeInputs.close':
            require(fn.__defaults__==(None,run_runtime_cleanup.__code__,run_runtime_cleanup.__defaults__,FunctionType,builtins.object.__getattribute__),'runtime close defaults differ')
        elif expected.co_qualname in ('LocalRuntimeInputs.prepare_consumer','LocalRuntimeInputs.consume_once'):
            require(fn.__defaults__==(LocalRuntimeInputs.close.__code__,LocalRuntimeInputs.close.__defaults__,runtime_seal.__code__,runtime_seal.__defaults__,LocalRuntimeInputs.entry.__code__,LocalRuntimeInputs.entry.__defaults__,LocalRuntimeInputs.source_bookend.__code__,LocalRuntimeInputs.source_bookend.__defaults__,check_bindings.__code__,check_bindings.__defaults__,held_consumer_helper.__code__,held_consumer_helper.__defaults__,globals(),FunctionType,builtins.object.__setattr__,BaseException,ValueError,builtins.type,builtins.bytes,builtins.len),'consumer held cleanup defaults differ')
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
    require(_NativeCleanupRoots.__bases__==_RuntimeCleanup.__bases__==(object,),'cleanup held class bases differ')
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
            _control_after_import=None,_audit_handed_off=False,_source_bookends=0,_import_profile_matched=False,
            _consumer_plan=None,_consume_state=None,_runtime_cleanup=None,_runtime_cleanup_seal=None,_runtime_cleanup_anchor=None).items():object.__setattr__(target,name,value)
        try:
            packet=capture_runtime_cleanup(target,namespace_specs,expected)
            object.__setattr__(target,'_runtime_cleanup',packet)
            seal_runtime_cleanup(target)
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


class _NativeCleanupRoots:
    __slots__=('resource','rows','held_rows','opened','metadata')
    def __new__(cls,*args,**kwargs):raise TypeError('native construction owns cleanup roots')
    def __setattr__(self,name,value):raise AttributeError('native cleanup roots are held')
    def __delattr__(self,name):raise AttributeError('native cleanup roots are held')


def capture_native_cleanup_roots(resource):
    # Runs inside _Resource.__init__, before either HANDLE is acquired. The
    # creating lease also retains this object in ownership[5] before open().
    names=('api','held','creator','pending','close_calls','guard','_early','cleanup_code','_close_impl',
           '_C','_W','_tuple','_getpid','_get_ident','_reject','_byref','_set_error','_get_error',
           '_DWORD','_WinError','_any','_unresolved')
    roots=object.__new__(_NativeCleanupRoots)
    object.__setattr__(roots,'resource',resource)
    object.__setattr__(roots,'rows',tuple((name,object.__getattribute__(resource,name)) for name in names))
    object.__setattr__(roots,'held_rows',tuple(resource.held.items()))
    object.__setattr__(roots,'opened',(None,None))
    metadata=[]
    values=[value for _,value in roots.rows]+[row[0] for _,row in roots.held_rows]
    for cls in (resource._unresolved,):
        metadata.append(('class',cls,tuple(vars(cls).items())))
        values.extend(vars(cls).values())
    for value in values:
        if type(value) is FunctionType:
            metadata.append(('function',value,(value.__code__,value.__defaults__,value.__kwdefaults__,value.__closure__)))
    require(type(resource.guard) is dict and type(resource.guard['events']) is list
            and (resource._early is None or type(resource._early) is dict),'exact native audit ledgers required')
    metadata.append(('events',resource.guard,resource.guard['events']))
    object.__setattr__(roots,'metadata',tuple(metadata))
    return roots


def verify_native_cleanup_roots(resource,roots,_get=object.__getattribute__,_type=type,_tuple=tuple,_reject=ValueError,_vars=vars):
    if _get(roots,'resource') is not resource or _get(resource,'_native_roots') is not roots:
        raise _reject('native construction root identity changed')
    for name,value in _get(roots,'rows'):
        if _get(resource,name) is not value:raise _reject('native construction root changed: '+name)
    held=_get(resource,'held');rows=_get(roots,'held_rows')
    if _type(held) is not dict or _tuple(held)!=_tuple(name for name,_ in rows):raise _reject('native API keyset changed')
    for name,row in rows:
        if held[name] is not row:raise _reject('native API row changed: '+name)
    for kind,value,expected in _get(roots,'metadata'):
        if kind=='class':
            actual=_tuple(_vars(value).items())
            if actual!=expected:raise _reject('native failure class changed')
        elif kind=='events':
            if value['events'] is not expected:raise _reject('native event ledger changed')
        elif not (value.__code__ is expected[0] and value.__defaults__ is expected[1]
                  and value.__kwdefaults__ is expected[2] and value.__closure__ is expected[3]):
            raise _reject('native cleanup function metadata changed')


def record_native_open(resource,index,handle):
    roots=resource._native_roots
    verify_native_cleanup_roots(resource,roots)
    require(index in (0,1) and roots.opened[index] is None and type(handle) is int and handle>0,
            'single actual native handle return required')
    values=list(roots.opened);values[index]=handle
    object.__setattr__(roots,'opened',tuple(values))


class _RuntimeCleanup:
    __slots__=('owner','source','creator','resource','roots','ownership','namespace','namespace_specs',
        'core_rows','core_check','entry_spec','bookend_spec','namespace_spec','namespace_proof',
        'modules','module','alias','system','absent','owner_slots',
        'boundary','boundary_spec','boundary_proof','boundary_state','boundary_type','boundary_slot',
        'binding_stage','execution_state','failure','lock','reentry','native_started','native_terminal','domain_errors','ledger')
    def __new__(cls,*args,**kwargs):raise TypeError('runtime transfer owns cleanup packet')
    def __setattr__(self,name,value):raise AttributeError('runtime cleanup packet is held')
    def __delattr__(self,name):raise AttributeError('runtime cleanup packet is held')
    def __reduce__(self):raise TypeError('runtime cleanup packet is process local')


def cleanup_root_image(packet,_get=object.__getattribute__,_id=id,_tuple=tuple):
    # Late-bound fields are committed in the original anchor journal. This
    # image binds only roots that are fixed before native ownership transfers.
    names=('owner','source','creator','resource','roots','ownership','namespace','namespace_specs','core_rows',
        'core_check','entry_spec','bookend_spec','namespace_spec','namespace_proof','modules','module','alias','system',
        'absent','owner_slots','lock','ledger')
    specs=('core_check','entry_spec','bookend_spec','namespace_spec','namespace_proof')
    return (_id(packet),_tuple(_id(_get(packet,name)) for name in names),
        _tuple(_tuple(_id(value) for value in _get(packet,name)) for name in specs),
        _get(packet,'creator'),_get(packet,'alias'),
        _id(_get(_get(packet,'roots'),'rows')),_id(_get(_get(packet,'roots'),'held_rows')),
        _id(_get(_get(packet,'roots'),'metadata')),_get(_get(packet,'roots'),'opened'))


def cleanup_binding_snapshot(journal,initial,_roots=(type,list,tuple,len,ValueError,range,BaseException,int,str,bool)):
    typ,list_,tup,length,reject,range_,base,int_,str_,bool_=_roots
    last=initial
    try:
        if typ(journal) is not list_ or not 1<=length(journal)<=3:raise reject('cleanup binding journal bounds changed')
        for index in range_(length(journal)):
            row=journal[index]
            if (typ(row) is not tup or length(row)!=4 or typ(row[0]) is not int_ or row[0]!=index
                    or row[1] is not (None if index==0 else last)
                    or typ(row[2]) is not str_ or row[2]!=('ARMED','BOUNDARY_SPEC','BOUNDARY_OBJECT')[index]
                    or typ(row[3]) is not tup or length(row[3])!=6):raise reject('cleanup binding journal prefix changed')
            if index==0 and row is not initial:raise reject('original cleanup binding record changed')
            if index==1 and (row[3][0] is not None or row[3][1] is None or row[3][2] is None or row[3][3:]!=(None,None,None)):
                raise reject('cleanup spec record changed')
            if index==2:
                state=row[3][3]
                if (typ(state) is not tup or length(state)!=8
                        or typ(state[0]) is not str_ or typ(state[7]) is not str_
                        or typ(state[1]) is not bool_ or typ(state[6]) is not bool_
                        or typ(state[2]) is not int_ or typ(state[3]) is not int_ or typ(state[4]) is not int_ or typ(state[5]) is not int_):raise reject('cleanup initial state shape changed')
            if index==2 and (row[3][0] is None or row[3][1] is not last[3][1] or row[3][2] is not last[3][2]
                    or row[3][3]!=('INSTALLING',True,0,0,0,0,False,'') or row[3][4] is None or row[3][5] is None):
                raise reject('cleanup object record changed')
            last=row
    except base as error:return last,error
    return last,None


def seal_runtime_cleanup(owner):
    require(owner._runtime_cleanup_anchor is None,'cleanup anchor is created once before ownership transfer')
    packet=owner._runtime_cleanup;image=cleanup_root_image(packet)
    names=('owner','source','creator','resource','roots','ownership','namespace','namespace_specs','core_rows',
        'core_check','entry_spec','bookend_spec','namespace_spec','namespace_proof','modules','module','alias','system',
        'absent','owner_slots','lock','ledger')
    initial=(0,None,'ARMED',(None,None,None,None,None,None))
    anchor=tuple((name,object.__getattribute__(packet,name)) for name in names)+(
        ('packet',packet),('root_image',image),('native_rows',packet.roots.rows),
        ('native_held_rows',packet.roots.held_rows),('native_metadata',packet.roots.metadata),
        ('initial_binding',initial),('binding_journal',[initial]))
    object.__setattr__(owner,'_runtime_cleanup_anchor',anchor)
    object.__setattr__(owner,'_runtime_cleanup_seal',image)


def commit_cleanup_binding(owner,stage,values,_append=list.append):
    anchor=owner._runtime_cleanup_anchor;owned=dict(anchor)
    require(owner._seal[0]==id(anchor) and owned['owner'] is owner,'same original cleanup anchor required')
    journal=owned['binding_journal'];last,error=cleanup_binding_snapshot(journal,owned['initial_binding'])
    if error is not None:raise error
    require((last[2],stage) in (('ARMED','BOUNDARY_SPEC'),('BOUNDARY_SPEC','BOUNDARY_OBJECT'))
            and type(values) is tuple and len(values)==6,'single next cleanup binding required')
    packet=owned['packet'];names=('boundary','boundary_spec','boundary_proof','boundary_state','boundary_type','boundary_slot')
    require(packet is owner._runtime_cleanup and packet.binding_stage==last[2]
            and all(object.__getattribute__(packet,name) is value for name,value in zip(names,last[3])),
            'previous cleanup binding mirror changed')
    record=(len(journal),last,stage,values)
    # One publication before any mirror mutation or boundary claim/hook effect.
    _append(journal,record)
    return record


def capture_runtime_cleanup(owner,namespace_specs,namespace_codes):
    resource=owner._resource;ownership=owner._ownership
    require(owner._phase=='PREPARING' and resource.owner is owner._source and len(ownership)==7
            and ownership[0] is resource and ownership[5] is resource._native_roots,'original precommit ownership required')
    roots=ownership[5];verify_native_cleanup_roots(resource,roots)
    live=ownership[6]
    require(live is resource._native_live and live[0] is roots and live[2] is resource.creator
            and tuple(resource.pending)==live[1] and roots.opened==tuple(row[0] for row in live[1])
            and resource.close_calls==[0,0],'original completed-open returns required')
    check_bindings(owner._bindings)
    methods=vars(LocalRuntimeInputs)
    spec=lambda fn:(FunctionType,fn.__code__,fn.__globals__,fn.__defaults__)
    namespace=owner._namespace;context=namespace_specs[2][2]
    require(namespace_specs[2][1]==namespace_codes['close_runtime_namespace'],'exact namespace cleanup source required')
    verifier=context['verify_helper_bindings']
    require(type(verifier) is FunctionType and verifier.__code__==namespace_codes['verify_helper_bindings']
            and verifier.__defaults__==(getattr,vars,type,ValueError,tuple,sorted),'exact namespace root verifier required')
    proof=(*spec(verifier),namespace._bindings);verifier(namespace._bindings)
    packet=object.__new__(_RuntimeCleanup)
    fields=dict(owner=owner,source=owner._source,creator=owner._creator,resource=resource,roots=roots,ownership=ownership,
        namespace=namespace,namespace_specs=namespace_specs,core_rows=owner._bindings,
        core_check=spec(check_bindings),entry_spec=spec(methods['entry']),bookend_spec=spec(methods['source_bookend']),
        namespace_spec=namespace_specs[2],namespace_proof=proof,modules=namespace._modules,module=namespace.module,
        alias=namespace._aliases[0],system=sys,absent=object(),owner_slots=tuple((name,methods[name]) for name in LocalRuntimeInputs.__slots__),
        boundary=None,boundary_spec=None,boundary_proof=None,boundary_state=None,boundary_type=None,boundary_slot=None,
        binding_stage='ARMED',execution_state='IDLE',failure=None,lock=Lock(),reentry=None,native_started=False,native_terminal=False,domain_errors=(),
        ledger=['IDLE',None,None,False,False,()])
    for name,value in fields.items():object.__setattr__(packet,name,value)
    return packet


def run_runtime_cleanup(packet,owner,primary=None,
        _roots=(object.__getattribute__,object.__setattr__,type,tuple,dict,list,len,any,FunctionType,BaseException,
                ValueError,LocalRuntimeUnresolved,RuntimeError.__new__,RuntimeError.__init__,os.getpid,get_ident,SimpleNamespace,
                verify_native_cleanup_roots.__code__,verify_native_cleanup_roots.__defaults__,
                cleanup_root_image.__code__,cleanup_root_image.__defaults__,id,int,str,bool,all,
                cleanup_binding_snapshot.__code__,cleanup_binding_snapshot.__defaults__)):
    (get,put,typ,tup,dict_,list_,length,any_,factory,base,reject,failure_type,new_error,init_error,getpid,ident,view_type,
     native_check,native_defs,image_code,image_defs,identity,int_,str_,bool_,all_,binding_code,binding_defs)=_roots
    anchor=get(owner,'_runtime_cleanup_anchor')
    if get(owner,'_seal')[0]!=identity(anchor):raise reject('owner-held cleanup anchor changed')
    owned=dict_(anchor)
    if owned['owner'] is not owner or owned['creator'][:2]!=(getpid(),ident()):raise reject('creating runtime cleanup required')
    resource=owned['resource'];roots=owned['roots']
    if get(resource,'owner') is not owner:raise reject('runtime cleanup ownership has not committed')
    original=owned['packet'];slots=dict_(owned['owner_slots']);ledger=owned['ledger']
    if typ(ledger) is not list_ or length(ledger)!=6:raise reject('owner-held cleanup ledger changed')
    fields=('execution_state','failure','reentry','native_started','native_terminal','domain_errors')
    mirror_errors=[]
    def record(name,value):
        ledger[fields.index(name)]=value
        try:put(original,name,value)
        except base as error:mirror_errors.append(('packet_mirror',error))
    def publish(cause,errors):
        failure=new_error(failure_type);init_error(failure,'local runtime ownership or cleanup unresolved')
        get(failure,'__dict__').update(owner=owner,primary=cause,secondary=tup(errors))
        # Publish the independent ledger and owner before the possibly damaged mirror.
        ledger[1]=failure;ledger[0]='UNRESOLVED'
        slots['_failure'].__set__(owner,failure);slots['_phase'].__set__(owner,'UNRESOLVED')
        try:put(original,'failure',failure);put(original,'execution_state','UNRESOLVED')
        except base as error:
            state=get(failure,'__dict__');state['secondary']=(*state['secondary'],('packet_publication',error))
        return failure
    image=factory(image_code,{'__builtins__':{}},'held_cleanup_root_image',image_defs)
    binding=factory(binding_code,{'__builtins__':{}},'held_cleanup_binding',binding_defs)
    latest,root_error=binding(owned['binding_journal'],owned['initial_binding'])
    late_names=('boundary','boundary_spec','boundary_proof','boundary_state','boundary_type','boundary_slot')
    for index in (0,1,2,3,4,5):owned[late_names[index]]=latest[3][index]
    try:
        if root_error is not None:raise root_error
        if get(original,'binding_stage')!=latest[2] or any_(get(original,late_names[index]) is not latest[3][index] for index in (0,1,2,3,4,5)):
            raise reject('runtime cleanup binding mirror changed')
        if (packet is not original or get(owner,'_runtime_cleanup') is not original
                or get(owner,'_runtime_cleanup_seal') is not owned['root_image'] or image(original)!=owned['root_image']):
            raise reject('runtime cleanup roots changed')
        if any_(get(original,name) is not ledger[index] for index,name in ((0,'execution_state'),(1,'failure'),(2,'reentry'),
                (3,'native_started'),(4,'native_terminal'),(5,'domain_errors'))):
            raise reject('runtime cleanup execution mirror changed')
    except base as error:root_error=error
    # A published failure is anchored independently of the packet mirror.
    if ledger[0]=='UNRESOLVED' and ledger[1] is not None:
        failure=ledger[1];state=get(failure,'__dict__')
        if typ(failure) is not failure_type or slots['_failure'].__get__(owner) is not failure or state.get('owner') is not owner:
            raise reject('original cleanup failure identity changed')
        raise failure from state['primary']
    lock=owned['lock']
    if not lock.acquire(False):
        error=ledger[2]
        if error is None:error=reject('runtime cleanup reentered');record('reentry',error)
        raise error
    try:
        state=ledger[0]
        if state=='CLOSED':
            rows=dict_(owned['native_rows'])
            try:
                if (get(roots,'rows') is not owned['native_rows'] or get(roots,'held_rows') is not owned['native_held_rows']
                        or get(roots,'metadata') is not owned['native_metadata']):raise reject('closed native construction roots changed')
                factory(native_check,{'__builtins__':{'dict':dict_}},'held_closed_native_roots',native_defs)(resource,roots)
            except base as error:root_error=error
            terminal=(root_error is None and ledger[1] is None and ledger[3] is ledger[4] is True
                and ledger[2] is None and ledger[5]==()
                and slots['_phase'].__get__(owner)=='CLOSED' and slots['_cleanup_started'].__get__(owner) is True
                and get(resource,'phase')=='CLOSED' and get(resource,'pending') is rows['pending']
                and get(resource,'close_calls') is rows['close_calls'] and rows['pending']==[None,None] and rows['close_calls']==[1,1]
                and not rows['guard']['active'] and not rows['guard']['self_live']
                and (rows['_early'] is None or not rows['_early']['active'] and not rows['_early']['sources_allowed']))
            if terminal:return
            failure=publish(primary if primary is not None else root_error,(('cleanup_terminal',reject('closed cleanup evidence changed')),))
            raise failure from get(failure,'__dict__')['primary']
        if state!='IDLE':
            failure=publish(primary,(('cleanup_state',reject('incomplete prior cleanup cannot retry')),))
            raise failure from primary
        errors=[]
        if root_error is not None:
            if primary is None:primary=root_error
            errors.append(('cleanup_roots',root_error))
        if ledger[1:]!=[None,None,False,False,()]:
            failure=publish(primary,(('cleanup_state',reject('dirty independent cleanup ledger')),))
            raise failure from primary
        record('execution_state','RUNNING');slots['_cleanup_started'].__set__(owner,True)
        def call(spec,*args):return factory(spec[1],spec[2],'held_source_cleanup_domain',spec[3])(*args)
        def proof(spec):
            return factory(spec[1],{'__builtins__':{},'dict':dict_,'type':typ},'held_cleanup_proof',spec[3])(spec[4])
        def boundary_state():
            boundary=owned['boundary'];slot=owned['boundary_slot'];initial=owned['boundary_state']
            if typ(boundary) is not owned['boundary_type'] or initial!=('INSTALLING',True,0,0,0,0,False,''):
                raise reject('original boundary binding changed')
            state=slot.__get__(boundary)
            if (typ(state) is not tup or length(state)!=8 or state[0] not in ('INSTALLING','ACTIVE','FAULTED','CLOSED')
                    or typ(state[1]) is not bool_ or typ(state[6]) is not bool_ or typ(state[7]) is not str_
                    or not all_(typ(value) is int_ and value>=0 for value in state[2:6])
                    or state[0]=='CLOSED' and (state[1] or not state[6])
                    or state[0] in ('INSTALLING','ACTIVE') and not state[1]
                    or not state[1] and not state[6]):
                raise reject('boundary cleanup state is malformed')
            return state
        try:
            if primary is None:primary=slots['_failure'].__get__(owner)
            try:
                if root_error is not None:raise root_error
                proof((*owned['core_check'],owned['core_rows']))
                if get(owner,'_resource') is not resource or get(owner,'_ownership') is not owned['ownership']:
                    raise reject('runtime cleanup owner references changed')
                if 'snapshot' in get(resource,'__dict__'):raise reject('resource snapshot shadowed')
                if get(owner,'_phase') in ('ADOPTED','IMPORTING','OBSERVED','LIVE'):
                    call(owned['entry_spec'],owner);call(owned['bookend_spec'],owner)
            except base as error:
                if primary is None:primary=error
                elif error is not root_error:errors.append(('runtime_bookend',error))
            boundary=owned['boundary']
            if boundary is not None:
                try:
                    boundary_state()
                    if root_error is not None:raise root_error
                    proof(owned['boundary_proof']);call(owned['boundary_spec'],boundary,primary)
                except base as error:errors.append(('import_boundary',error))
                try:
                    state=boundary_state()
                    if state[1] or not state[6]:
                        owned['boundary_slot'].__set__(boundary,('FAULTED',False,*state[2:6],True,state[7]))
                        errors.append(('boundary_emergency_retirement',reject('boundary required emergency deactivation')))
                except base as error:errors.append(('boundary_retirement',error))
            try:
                if root_error is not None:raise root_error
                proof(owned['namespace_proof']);call(owned['namespace_spec'],owned['namespace'],owner)
            except base as error:
                errors.append(('namespace',error))
                try:
                    modules=owned['modules'];module=owned['module'];alias=owned['alias'];absent=owned['absent']
                    if get(owned['system'],'modules') is not modules or typ(modules) is not dict_:
                        raise reject('original namespace container unavailable')
                    actual=dict_.get(modules,alias,absent)
                    if actual is module:dict_.__delitem__(modules,alias)
                    elif actual is not absent:raise reject('foreign namespace alias preserved')
                except base as error:errors.append(('namespace_retirement',error))
        except base as error:errors.append(('cleanup_control',error))
        finally:
            try:
                if (get(roots,'rows') is not owned['native_rows'] or get(roots,'held_rows') is not owned['native_held_rows']
                        or get(roots,'metadata') is not owned['native_metadata']):raise reject('native construction capsule changed')
                factory(native_check,{'__builtins__':{'dict':dict_}},'held_native_construction_roots',native_defs)(resource,roots)
                rows=dict_(owned['native_rows']);pending=rows['pending'];calls=rows['close_calls'];live=owned['ownership'][6]
                if (get(owner,'_ownership') is not owned['ownership'] or get(owner,'_resource') is not resource
                        or get(resource,'owner') is not owner or get(resource,'creator')!=owned['creator'] or get(resource,'_native_live') is not live):
                    raise reject('original native owner changed')
                if typ(pending) is not list_ or typ(calls) is not list_ or length(pending)!=2 or calls!=[0,0] or tup(pending)!=live[1]:
                    raise reject('original native ledger changed before close')
                view=view_type(**rows);view.owner=owner;view.phase=get(resource,'phase');view.held=dict_(owned['native_held_rows'])
                record('native_started',True)
                try:
                    factory(rows['cleanup_code'],{'BaseException':base,'__builtins__':{}},'held_source_native_kernel',(None,))(view,owner,primary)
                finally:
                    put(resource,'phase',get(view,'phase'))
                    terminal=(get(view,'phase')=='CLOSED' and get(resource,'phase')=='CLOSED' and tup(pending)==(None,None)
                        and calls==[1,1] and get(resource,'pending') is pending and get(resource,'close_calls') is calls
                        and get(view,'pending') is pending and get(view,'close_calls') is calls and not rows['guard']['self_live']
                        and (rows['_early'] is None or not rows['_early']['sources_allowed']))
                    factory(native_check,{'__builtins__':{'dict':dict_}},'held_post_native_roots',native_defs)(resource,roots)
                    record('native_terminal',terminal)
            except base as error:errors.append(('native',error))
            try:
                rows=dict_(owned['native_rows']);rows['guard']['active']=False
                if rows['_early'] is not None:rows['_early']['active']=False
            except base as error:errors.append(('old_hook_deactivation',error))
            if ledger[2] is not None:
                if primary is None:primary=ledger[2]
                else:errors.append(('cleanup_reentry',ledger[2]))
            if not ledger[4]:errors.append(('pending_handles',reject('native cleanup unresolved')))
            record('domain_errors',tup(errors))
            errors.extend(mirror_errors)
            if primary is not None or errors:
                failure=publish(primary,errors)
                raise failure from primary
            record('execution_state','CLOSED')
            if mirror_errors:
                failure=publish(primary,mirror_errors)
                raise failure from primary
            slots['_phase'].__set__(owner,'CLOSED')
    except base as error:
        if ledger[1] is not None:raise ledger[1] from get(ledger[1],'__dict__')['primary']
        failure=publish(primary,(('cleanup_control',error),))
        raise failure from primary
    finally:lock.release()

def runtime_seal(owner,phase=None,_id=id,_sha=sha256,_tuple=tuple):
    return _tuple(_id(value) for value in (owner._runtime_cleanup_anchor,owner._source,owner._namespace,owner._resource,owner._ownership,owner._sources,
        owner._cleanup_seal,owner._bindings,owner._pre_control,owner._namespace_specs,owner._namespace_snapshot,owner._boundary,
        owner._boundary_entry,owner._boundary_finish,owner._boundary_phase,owner._boundary_profile,owner._boundary_pending,owner._boundary_bindings,owner._adapter,owner._adapter_bindings,owner._retention,
        owner._control_after_import,owner._consumer_plan,owner._runtime_cleanup,owner._runtime_cleanup_seal))+(_sha(owner._raw).digest(),owner._creator,owner._phase if phase is None else phase,
        owner._audit_handed_off,owner._import_profile_matched,owner._consume_state)


def held_consumer_helper(owner,name):
    require(name in ('prepare_consumer_plan','verify_consumer_plan','invoke_consumer_plan'),'fixed consumer helper required')
    context=owner._namespace_specs[1][2]
    rows=[row for row in owner._namespace._bindings if row[0] is context and row[1]==name]
    require(len(rows)==1,'original consumer helper binding required')
    context,key,fn,metadata=rows[0]
    require(type(fn) is FunctionType and type(metadata) is tuple and metadata[2] is metadata[3] is None,'closed consumer helper required')
    return FunctionType(metadata[0],context,'held_'+key,metadata[1])


class LocalRuntimeInputs:
    """Exact native owner for one namespace/import episode; never role authority."""
    __slots__=('_source','_namespace','_resource','_ownership','_cleanup_seal','_sources','_raw','_bindings','_pre_control','_creator','_namespace_specs',
        '_phase','_failure','_cleanup_started','_boundary','_boundary_entry','_boundary_finish','_boundary_phase','_boundary_profile','_boundary_pending','_boundary_bindings',
        '_adapter','_adapter_bindings','_retention','_control_after_import','_audit_handed_off','_source_bookends','_import_profile_matched',
        '_consumer_plan','_consume_state','_namespace_snapshot','_seal','_runtime_cleanup','_runtime_cleanup_seal','_runtime_cleanup_anchor')
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
        if self._consumer_plan is not None:
            held_consumer_helper(self,'verify_consumer_plan')(self,self._consumer_plan)
        else:require(self._consume_state is None,'consumer state without immutable plan')
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
        packet=object.__getattribute__(self,'_runtime_cleanup')
        require(packet.owner is self and packet.binding_stage=='ARMED' and cleanup_root_image(packet)==self._runtime_cleanup_seal,
                'single creating cleanup boundary preparation')
        commit_cleanup_binding(self,'BOUNDARY_SPEC',(None,finish_spec,proof,None,None,None))
        object.__setattr__(packet,'boundary_spec',finish_spec)
        object.__setattr__(packet,'boundary_proof',proof)
        object.__setattr__(packet,'binding_stage','BOUNDARY_SPEC')
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
        packet=object.__getattribute__(self,'_runtime_cleanup')
        require(packet.owner is self and packet.binding_stage=='BOUNDARY_SPEC' and cleanup_root_image(packet)==self._runtime_cleanup_seal,
                'single cleanup boundary ownership')
        state_slot=vars(type(boundary))['_state'];initial=state_slot.__get__(boundary)
        require(initial==('INSTALLING',True,0,0,0,0,False,''),'original installing boundary state required')
        commit_cleanup_binding(self,'BOUNDARY_OBJECT',(boundary,packet.boundary_spec,packet.boundary_proof,initial,type(boundary),state_slot))
        object.__setattr__(packet,'boundary',boundary)
        object.__setattr__(packet,'boundary_state',initial)
        object.__setattr__(packet,'boundary_type',type(boundary));object.__setattr__(packet,'boundary_slot',state_slot)
        object.__setattr__(packet,'binding_stage','BOUNDARY_OBJECT')
        object.__setattr__(self,'_seal',runtime_seal(self))
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
        self.entry();return observed
    def close(self,primary=None,_code=run_runtime_cleanup.__code__,_defs=run_runtime_cleanup.__defaults__,
              _fn=FunctionType,_get=object.__getattribute__):
        packet=_get(self,'_runtime_cleanup')
        return _fn(_code,{'__builtins__':{}},'held_source_runtime_cleanup',_defs)(packet,self,primary)
    def prepare_consumer(self,_close_code=close.__code__,_close_defs=close.__defaults__,_seal_code=runtime_seal.__code__,_seal_defs=runtime_seal.__defaults__,_entry_code=entry.__code__,_entry_defs=entry.__defaults__,_bookend_code=source_bookend.__code__,_bookend_defs=source_bookend.__defaults__,_check_code=check_bindings.__code__,_check_defs=check_bindings.__defaults__,_helper_code=held_consumer_helper.__code__,_helper_defs=held_consumer_helper.__defaults__,_ctx=globals(),_fn=FunctionType,_put=object.__setattr__,_base=BaseException,_reject=ValueError,_type=type,_bytes=bytes,_len=len):
        close=_fn(_close_code,_ctx,'held_consumer_cleanup',_close_defs)
        seal=_fn(_seal_code,_ctx,'held_consumer_seal',_seal_defs)
        try:
            if seal(self)!=self._seal:raise _reject('consumer immutable state differs')
            _fn(_check_code,_ctx,'held_consumer_core_roots',_check_defs)(self._bindings)
            entry=_fn(_entry_code,_ctx,'held_consumer_entry',_entry_defs);entry(self)
            if not (self._phase=='IMPORTING' and self._boundary is not None and self._adapter is None
                and self._consumer_plan is None and self._consume_state is None):raise _reject('single pre-LIVE consumer preparation required')
            dispatch=_fn(_helper_code,_ctx,'held_consumer_dispatch',_helper_defs)
            plan=dispatch(self,'prepare_consumer_plan')(self)
            _put(self,'_consumer_plan',plan);_put(self,'_consume_state','PREPARED');_put(self,'_seal',seal(self))
            entry(self);return self
        except _base as primary:
            close(self,primary)
            raise
    def consume_once(self,consumer_id,raw_inputs,_close_code=close.__code__,_close_defs=close.__defaults__,_seal_code=runtime_seal.__code__,_seal_defs=runtime_seal.__defaults__,_entry_code=entry.__code__,_entry_defs=entry.__defaults__,_bookend_code=source_bookend.__code__,_bookend_defs=source_bookend.__defaults__,_check_code=check_bindings.__code__,_check_defs=check_bindings.__defaults__,_helper_code=held_consumer_helper.__code__,_helper_defs=held_consumer_helper.__defaults__,_ctx=globals(),_fn=FunctionType,_put=object.__setattr__,_base=BaseException,_reject=ValueError,_type=type,_bytes=bytes,_len=len):
        close=_fn(_close_code,_ctx,'held_consumer_cleanup',_close_defs)
        seal=_fn(_seal_code,_ctx,'held_consumer_seal',_seal_defs)
        if self._phase in ('CLOSED','UNRESOLVED') and self._resource.phase=='CLOSED':raise _reject('consumer owner is terminal')
        result=None;primary=None
        try:
            if seal(self)!=self._seal:raise _reject('consumer immutable state differs')
            _fn(_check_code,_ctx,'held_consumer_core_roots',_check_defs)(self._bindings)
            entry=_fn(_entry_code,_ctx,'held_consumer_entry',_entry_defs);entry(self)
            if not (self._phase=='LIVE' and self._import_profile_matched and self._consume_state=='PREPARED'):
                raise _reject('one prepared profile-matched LIVE consumption required')
            _put(self,'_consume_state','RUNNING');_put(self,'_seal',seal(self))
            bookend=_fn(_bookend_code,_ctx,'held_consumer_sources',_bookend_defs);bookend(self)
            dispatch=_fn(_helper_code,_ctx,'held_consumer_dispatch',_helper_defs)
            result=dispatch(self,'invoke_consumer_plan')(self,consumer_id,raw_inputs)
            entry(self);bookend(self)
            if _type(result) is not _bytes or _len(result)>2048:raise _reject('bounded consumer bytes required')
            if self._consume_state!='RUNNING':raise _reject('consumer state changed during invocation')
            _put(self,'_consume_state','CONSUMED');_put(self,'_seal',seal(self))
        except _base as error:
            primary=error;result=None
            if seal(self)==self._seal:
                _put(self,'_consume_state','FAILED');_put(self,'_seal',seal(self))
        close(self,primary)
        if primary is not None:raise primary
        return result
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
        owner._ownership=(resource,resource.creator,resource.cleanup_code,FunctionType,BaseException,resource._native_roots); owner._phase='OPENING'
        owner._cleanup_seal=(id(resource),id(owner._ownership),id(owner._ownership[2]),id(owner._ownership[3]),id(owner._ownership[4]),resource.creator)
        native_live=resource.open()
        owner._ownership=(*owner._ownership,native_live)
        owner._cleanup_seal=(id(resource),id(owner._ownership),id(owner._ownership[2]),id(owner._ownership[3]),id(owner._ownership[4]),resource.creator)
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


def producer_helper_paths():
    return dict(bootstrap_loader=str(ROOT/'experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v5.py'),
        p1_permission=str(ROOT/'experiments/staged_rts24_saved_fresh_p1_permission_v1.py'),
        coordinator=str(ROOT/'experiments/staged_rts24_saved_fresh_complete_producer_v2.py'),
        bootstrap_actor=str(ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_actor_v2.py'),
        construction=str(ROOT/'experiments/staged_rts24_saved_fresh_producer_bootstrap_v7.py'),
        project_graph=str(ROOT/'experiments/staged_rts24_saved_fresh_producer_project_graph_v3.py'),
        lifecycle=str(ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v6.py'),
        utilities=str(ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v1.py'),
        capture=str(ROOT/'experiments/staged_rts24_saved_fresh_prebound_expectation_code_v3.py'),
        predecessor_checkpoint=str(ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v12_non_authoritative/checkpoint.json'),
        predecessor_registration=str(ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v12_non_authoritative/registration.json'))


def check_producer_helpers(plan):
    paths=producer_helper_paths();refs=plan['producer_helpers']
    require(type(refs) is dict and set(refs)==set(paths),'closed producer helper references')
    for key,path in paths.items():
        ref=refs[key]
        require(type(ref) is dict and set(ref)=={'path','pin'} and ref['path']==path,'fixed producer helper path')
        value=ref['pin']
        require(type(value) is dict and set(value)=={'bytes','sha256'} and type(value['bytes']) is int
            and 0<value['bytes']<=1048576 and type(value['sha256']) is str and len(value['sha256'])==64
            and all(c in '0123456789abcdef' for c in value['sha256']),'closed producer helper pin')
    require(plan['import_helper']['path']==str(ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v4.py'),
        'construction B_S source required')


def construction_graph_contract():
    return {'schema': 'staged_saved_F_bootstrap_graph_stop_contract_v1', 'graph_call_stop': 256, 'graph_image_bytes_stop': 4194304, 'prior_construction_calls': 43, 'observed_complete_calls': None, 'whole_workflow_admitted': False}
