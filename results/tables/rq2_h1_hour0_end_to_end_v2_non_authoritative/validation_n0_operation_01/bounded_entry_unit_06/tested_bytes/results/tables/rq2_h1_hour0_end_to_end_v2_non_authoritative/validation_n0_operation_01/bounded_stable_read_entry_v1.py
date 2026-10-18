"""Configured Windows/CPython entry: bound one canonical stable reader's read size.

All original stat/open/fstat/read/pathname observations still execute. There is
no source/result cache. This adds caller-frame audit events and a temporary
Path.open wrapper; transparency to audit hooks is outside this entry contract.
"""
from hashlib import sha256
import io
import os
from pathlib import Path
import sys
from threading import get_ident
import types

from performance import code_read_lease as code
from experiments import h1_raw_ingress_development_v1 as raw

SCHEMA='h1_bounded_stable_read_entry_v1'
RAW_SHA256='df59ba543655307f0aae369bebf85e46d5ed94a3525f1a7f72f718fe744b598a'


def _bind():
    records={};proxies={};active=[None];entry_methods=proxy_methods=()
    path_type=Path;open_path=Path.open;open_io=io.open
    read_bytes=Path.read_bytes;frame_of=sys._getframe
    get_trace,get_profile=sys.gettrace,sys.getprofile
    raw_function=raw.read_stable;raw_code=raw_function.__code__;raw_globals=vars(raw)
    raw_defaults,raw_keywords=raw_function.__defaults__,raw_function.__kwdefaults__
    raw_name=raw.__file__
    raw_path=Path(raw.__file__).resolve(strict=True)
    own_path=Path(__file__).resolve(strict=True)
    code_path=Path(code.__file__).resolve(strict=True)
    implementation=dict(schema=SCHEMA,python=sys.version,implementation=sys.implementation.name,
        cache_tag=sys.implementation.cache_tag,platform=sys.platform,
        raw_source_sha256=RAW_SHA256,entry_sha256=sha256(own_path.read_bytes()).hexdigest(),
        code_lease_sha256=sha256(code_path.read_bytes()).hexdigest(),
        audit_hook_transparency_proven=False,source_or_result_cache=False)
    code_type=code.CodeReadLease
    original_methods=tuple((name,value,value.__code__) for name,value in vars(code_type).items()
        if type(value) is types.FunctionType)
    close_handle=code._kernel.CloseHandle
    code_identity=code._identity
    make_function,make_method=types.FunctionType,types.MethodType
    # Original cleanup is callable even after an ordinary class alias changes.
    release_globals=dict(code_type._release.__globals__)
    release_globals['_kernel']=types.SimpleNamespace(CloseHandle=close_handle)
    release=make_function(code_type._release.__code__,release_globals,'release')
    enter_code=code_type.__enter__
    exit_code=make_function(code_type.__exit__.__code__,dict(code_type.__exit__.__globals__),'exit')
    code_check=code_type._check_hooks
    code_receipt=code_type.receipt
    code_helpers=tuple((name,getattr(code,name),getattr(code,name).__code__)
        for name in ('_identity','_bytes','_key'))
    max_read=sys.maxsize

    def method_state(value):
        if type(value) is not types.FunctionType:return (value,)
        return value,value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__)

    def code_dispatch():
        return (code.CodeReadLease is code_type
            and all(vars(code_type).get(name) is fn and fn.__code__ is instructions
                for name,fn,instructions in original_methods)
            and all(getattr(code,name) is fn and fn.__code__ is instructions
                for name,fn,instructions in code_helpers))

    def row(owner):
        result=records.get(id(owner))
        if result is None or result['owner'] is not owner:
            raise ValueError('original bounded stable-read entry required')
        return result

    def fail(value,message):
        if value['failure'] is None:value['failure']=message
        raise ValueError(message)

    def original_check(value,require_creator=True):
        if value['failure'] is not None:
            raise ValueError('bounded stable-read entry is poisoned: '+value['failure'])
        if (value['state']!='active' or active[0] is not value
                or value['creator'][0]!=os.getpid()
                or require_creator and value['creator'][1]!=get_ident()
                or path_type.open is not value['wrapper'] or io.open is not open_io
                or sys._getframe is not frame_of or sys.gettrace is not get_trace or sys.getprofile is not get_profile
                or get_trace() is not None or get_profile() is not None
                or raw.read_stable is not raw_function or raw_function.__code__ is not raw_code
                or raw_function.__globals__ is not raw_globals or raw.__file__!=raw_name
                or raw_function.__defaults__ is not raw_defaults or raw_function.__kwdefaults__ is not raw_keywords
                or Path is not path_type or SCHEMA!=implementation['schema']
                or RAW_SHA256!=implementation['raw_source_sha256']
                or sys.maxsize!=max_read or sys.version!=implementation['python']
                or sys.platform!=implementation['platform']
                or code.CodeReadLease is not code_type
                or any(getattr(code,name) is not fn or fn.__code__ is not instructions
                    for name,fn,instructions in code_helpers)
                or any(vars(code_type).get(name) is not fn or fn.__code__ is not instructions
                    for name,fn,instructions in original_methods)
                or any(method_state(vars(cls).get(name))!=state
                    for cls,name,state in (*entry_methods,*proxy_methods))):
            fail(value,'bounded stable-read entry dispatch or lifetime changed')
        wrapper=value['wrapper']
        if (wrapper.__code__ is not value['wrapper_code']
                or wrapper.__defaults__ is not value['wrapper_defaults']
                or wrapper.__kwdefaults__ is not value['wrapper_keywords']
                or tuple((id(cell),id(cell.cell_contents)) for cell in wrapper.__closure__ or ())!=value['wrapper_closure']):
            fail(value,'bounded stable-read wrapper code changed')
        lease=value['code_owner']
        if (lease._state!='active' or lease._cached_read is not value['code_wrapper']
                or path_type.read_bytes is not value['code_wrapper']
                or tuple(lease._handles)!=value['handles'] or lease._release is not value['release']
                or code_identity(value['raw_handle'])!=value['raw_identity']):
            fail(value,'owned immutable raw-reader code lease changed')
        code_check(lease)

    def check(value,require_creator=True):
        try:return original_check(value,require_creator)
        except BaseException as error:
            if value['failure'] is None:
                try:value['failure']=repr(error)
                except BaseException:value['failure']='entry check failed'
            raise

    def proxy_row(proxy,*,validate=True):
        p=proxies.get(id(proxy))
        if p is None or p['proxy'] is not proxy:raise ValueError('original active bounded-read stream required')
        if validate:check(p['entry'])
        if p['closed']:fail(p['entry'],'closed bounded stable-read stream')
        return p

    def forget(p):
        p['closed']=True;p['entry']['streams'].remove(p);proxies.pop(id(p['proxy']),None)

    class Proxy:
        __slots__=()
        def __init__(self,record):record['proxy']=self;proxies[id(self)]=record
        def __enter__(self):
            p=proxy_row(self)
            try:
                p['reader']=p['stream'].__enter__()
                return self
            except BaseException as error:
                try:p['stream'].close()
                except BaseException as secondary:error.add_note('stable-read enter cleanup: '+repr(secondary))
                finally:forget(p)
                raise
        def fileno(self):return proxy_row(self)['reader'].fileno()
        def read(self,n=-1):
            p=proxy_row(self);value=p['entry']
            if type(n) is int and n==p['original_n']:
                value['hits']+=1;value['original_requested_bytes']+=n
                value['actual_requested_bytes']+=p['bounded_n']
                return p['reader'].read(p['bounded_n'])
            value['other_read_calls']+=1
            return p['reader'].read(n)
        def __exit__(self,kind,error,tb):
            p=proxy_row(self,validate=False)
            try:return p['stream'].__exit__(kind,error,tb)
            finally:
                if not p['closed']:forget(p)

    class BoundedStableReadLease:
        def __init__(self,expected,*,root):
            pins={path_type(p):pin for p,pin in expected.items()}
            required={raw_path:RAW_SHA256,own_path:implementation['entry_sha256'],
                code_path:implementation['code_lease_sha256']}
            if any(pins.get(path)!=pin for path,pin in required.items()):
                raise ValueError('entry, raw reader and code owner require exact held source pins')
            records[id(self)]=dict(owner=self,expected=pins,root=path_type(root),state='new',
                creator=(os.getpid(),get_ident()),failure=None,streams=[],hits=0,
                original_requested_bytes=0,actual_requested_bytes=0,other_read_calls=0,
                fallback_opens=0,code_owner=None)
        def __enter__(self):
            value=row(self)
            if (value['state']!='new' or active[0] is not None
                    or value['creator']!=(os.getpid(),get_ident())):
                raise ValueError('single-use nonnested creating-thread stable-read entry required')
            if (sys.platform!='win32' or sys.implementation.name!='cpython'
                    or path_type.open is not open_path or path_type.read_bytes is not read_bytes
                    or io.open is not open_io or sys._getframe is not frame_of
                    or get_trace() is not None or get_profile() is not None or not code_dispatch()):
                raise ValueError('configured untraced Windows/CPython entry required')
            lease=code_type(value['expected'],root=value['root'])
            value['code_owner']=lease
            private_release=make_method(release,lease);lease._release=private_release
            value['release']=private_release
            try:
                enter_code(lease)
                handle=lease._files[raw_path]
                value.update(code_wrapper=lease._cached_read,handles=tuple(lease._handles),
                    raw_handle=handle,raw_identity=code_identity(handle))
                def opening(path,*args,**kwargs):
                    frame=frame_of(1)
                    try:
                        target=frame.f_code is raw_code and frame.f_globals is raw_globals
                        check(value,require_creator=target)
                        if frame.f_code is raw_code and frame.f_globals is not raw_globals:
                            fail(value,'canonical stable-reader globals changed')
                        if not target:
                            value['fallback_opens']+=1
                            return open_path(path,*args,**kwargs)
                        before=frame.f_locals.get('before');cap=frame.f_locals.get('cap')
                        if (frame.f_locals.get('path') is not path or args!=('rb',) or kwargs
                                or type(before) is not tuple or len(before)!=5
                                or any(type(part) is not int for part in before)
                                or type(cap) is not int or not 0<=before[2]<=cap<=max_read-1):
                            fail(value,'exact canonical stable-reader open contract changed')
                        stream=open_path(path,*args,**kwargs)
                        p=dict(entry=value,stream=stream,reader=stream,closed=False,
                            original_n=cap+1,bounded_n=before[2]+1)
                        value['streams'].append(p)
                        return Proxy(p)
                    finally:del frame
                value['wrapper']=opening
                value.update(wrapper_code=opening.__code__,wrapper_defaults=opening.__defaults__,
                    wrapper_keywords=opening.__kwdefaults__,wrapper_closure=tuple(
                        (id(cell),id(cell.cell_contents)) for cell in opening.__closure__ or ()))
                active[0]=value;value['state']='active';path_type.open=opening
                check(value)
                return self
            except BaseException:
                if path_type.open is value.get('wrapper'):path_type.open=open_path
                active[0]=None;value['state']='closed'
                if lease._state=='active':exit_code(lease,None,None,None)
                raise
        def receipt(self):
            value=row(self);check(value)
            return dict(implementation,exact_stable_read_calls=value['hits'],
                original_requested_bytes=value['original_requested_bytes'],
                actual_requested_bytes=value['actual_requested_bytes'],
                other_read_calls=value['other_read_calls'],fallback_opens=value['fallback_opens'],
                active_streams=len(value['streams']),first_failure=value['failure'],
                code_lease=code_receipt(value['code_owner']),
                formal_result=False,formal_execution_ready=False,resource_admission=False,
                native_execution_authorized=False)
        def __exit__(self,kind,error,tb):
            value=row(self)
            if value['creator']!=(os.getpid(),get_ident()):
                raise ValueError('stable-read cleanup requires creating thread')
            if value['state']=='closed':return False
            failures=[]
            try:check(value)
            except BaseException as failure:failures.append(failure)
            if value['streams']:
                failures.append(ValueError('active bounded stable-read stream at entry exit'))
                for p in tuple(value['streams']):
                    try:p['stream'].close()
                    except BaseException as failure:failures.append(failure)
                    finally:forget(p)
            if path_type.open is value.get('wrapper'):path_type.open=open_path
            else:failures.append(ValueError('foreign Path.open replacement retained during cleanup'))
            try:exit_code(value['code_owner'],kind,error,tb)
            except BaseException as failure:failures.append(failure)
            finally:value['state']='closed';active[0]=None
            if failures:
                if value['failure'] is None:value['failure']=repr(failures[0])
                if error is not None:
                    for failure in failures:error.add_note('bounded stable-read cleanup: '+repr(failure))
                else:
                    for failure in failures[1:]:failures[0].add_note('additional cleanup: '+repr(failure))
                    raise failures[0]
            return False
    entry_methods=tuple((BoundedStableReadLease,name,method_state(fn))
        for name,fn in vars(BoundedStableReadLease).items() if type(fn) is types.FunctionType)
    proxy_methods=tuple((Proxy,name,method_state(fn))
        for name,fn in vars(Proxy).items() if type(fn) is types.FunctionType)
    return BoundedStableReadLease


BoundedStableReadLease=_bind()
del _bind
