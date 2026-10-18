"""Versioned reader entry with complete self-checks at open and stream exit.

All original stat/open/fstat/read/pathname observations still execute. There is
no source/result cache. Between those checks, every dispatch frontier verifies
the next proxy methods before and after the underlying callback. Unlike v2,
self-dispatch drift can be rejected after actual I/O; no raw.read_stable result
escapes before the terminal self-check. Audit-hook transparency is outside this contract.
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

SCHEMA='h1_bounded_stable_read_entry_v3'
RAW_SHA256='df59ba543655307f0aae369bebf85e46d5ed94a3525f1a7f72f718fe744b598a'


def _bind():
    records={};proxies={};active=[None];entry_methods=proxy_methods=();proxy_frontier={}
    namespace=globals();os_module,sys_module,io_module,raw_module,code_module,types_module=os,sys,io,raw,code,types
    pid_of,thread_of=os.getpid,get_ident
    function_type=types.FunctionType
    path_type=Path;open_path=Path.open;open_io=io.open
    read_bytes=Path.read_bytes;frame_of=sys._getframe
    get_trace,get_profile=sys.gettrace,sys.getprofile
    implementation_object=sys.implementation
    original_add_note=BaseException.add_note
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
        guard_schedule='non_target_route__target_open_exit_full__enter_fstat1_read_fstat2_frontier',
        entry_self_guard_failure_order_identical_to_v2=False,
        raw_scientific_io_observations_preserved=True,
        drift_after_open_can_precede_actual_io=True,
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
    private_code_check=make_function(code_check.__code__,dict(code_check.__globals__),'private_code_check')
    code_receipt=code_type.receipt
    code_helpers=tuple((name,getattr(code,name),getattr(code,name).__code__)
        for name in ('_identity','_bytes','_key'))
    max_read=sys.maxsize
    aliases=tuple((name,namespace[name]) for name in ('os','sys','io','raw','code','types','Path','get_ident','sha256'))
    kernel=code._kernel
    kernel_entries=tuple((name,getattr(kernel,name),tuple(getattr(kernel,name).argtypes),getattr(kernel,name).restype)
        for name in ('CreateFileW','CloseHandle','GetFileInformationByHandleEx','GetFileSizeEx','SetFilePointerEx','ReadFile'))
    code_dependencies=tuple((name,getattr(code,name)) for name in (
        '_kernel','_FileId','_Attributes','ctypes','wintypes','os','Path','stat','MappingProxyType','RLock','sha256'))

    def describe(error):
        try:return repr(error)
        except BaseException:return '<exception repr failed>'

    def note(error,message):
        try:original_add_note(error,message)
        except BaseException:pass

    def fixed_aliases():
        if (any(namespace.get(name) is not value for name,value in aliases)
                or os_module.getpid is not pid_of or namespace.get('get_ident') is not thread_of
                or any(getattr(code_module,name) is not value for name,value in code_dependencies)
                or any(getattr(kernel,name) is not fn or tuple(fn.argtypes)!=arguments or fn.restype is not result
                    for name,fn,arguments,result in kernel_entries)):
            raise ValueError('definition-time stable-read entry module or creator binding changed')

    def method_state(value):
        if type(value) is not function_type:return (value,)
        return value,value.__code__,value.__defaults__,value.__kwdefaults__

    def same_method(value,state):
        return (len(state)==4 and type(value) is function_type and value is state[0]
            and value.__code__ is state[1] and value.__defaults__ is state[2]
            and value.__kwdefaults__ is state[3])

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

    def route_check(value,require_creator=True):
        value['route_checks']+=1
        try:
            if value['failure'] is not None:raise ValueError('bounded stable-read entry is poisoned: '+value['failure'])
            lease=value['code_owner'];wrapper=value['wrapper']
            if (value['state']!='active' or active[0] is not value or value['creator'][0]!=pid_of()
                    or require_creator and value['creator'][1]!=thread_of()
                    or path_type.open is not wrapper or io_module.open is not open_io
                    or sys_module._getframe is not frame_of
                    or raw_module.read_stable is not raw_function or raw_function.__code__ is not raw_code
                    or raw_function.__globals__ is not raw_globals or raw_module.__file__!=raw_name
                    or raw_function.__defaults__ is not raw_defaults or raw_function.__kwdefaults__ is not raw_keywords
                    or wrapper.__code__ is not value['wrapper_code']
                    or wrapper.__defaults__ is not value['wrapper_defaults']
                    or wrapper.__kwdefaults__ is not value['wrapper_keywords']
                    or tuple((id(cell),id(cell.cell_contents)) for cell in wrapper.__closure__ or ())!=value['wrapper_closure']
                    or lease._state!='active' or lease._cached_read is not value['code_wrapper']
                    or path_type.read_bytes is not value['code_wrapper']
                    or lease._release is not value['release'] or lease._check_hooks is not value['private_code_check']):
                fail(value,'bounded stable-read route or lifetime changed')
        except BaseException as error:
            if value['failure'] is None:value['failure']=describe(error)
            raise

    def original_check(value,require_creator=True):
        fixed_aliases()
        if value['failure'] is not None:
            raise ValueError('bounded stable-read entry is poisoned: '+value['failure'])
        if (value['state']!='active' or active[0] is not value
                or value['creator'][0]!=pid_of()
                or require_creator and value['creator'][1]!=thread_of()
                or path_type.open is not value['wrapper'] or io_module.open is not open_io
                or sys_module._getframe is not frame_of or sys_module.gettrace is not get_trace or sys_module.getprofile is not get_profile
                or get_trace() is not None or get_profile() is not None
                or raw_module.read_stable is not raw_function or raw_function.__code__ is not raw_code
                or raw_function.__globals__ is not raw_globals or raw_module.__file__!=raw_name
                or raw_function.__defaults__ is not raw_defaults or raw_function.__kwdefaults__ is not raw_keywords
                or Path is not path_type or SCHEMA!=implementation['schema']
                or RAW_SHA256!=implementation['raw_source_sha256']
                or sys_module.maxsize!=max_read or sys_module.version!=implementation['python']
                or sys_module.platform!=implementation['platform']
                or sys_module.implementation is not implementation_object
                or implementation_object.name!=implementation['implementation']
                or implementation_object.cache_tag!=implementation['cache_tag']
                or code_module.CodeReadLease is not code_type
                or any(getattr(code_module,name) is not fn or fn.__code__ is not instructions
                    for name,fn,instructions in code_helpers)
                or any(vars(code_type).get(name) is not fn or fn.__code__ is not instructions
                    for name,fn,instructions in original_methods)
                or any(not same_method(vars(cls).get(name),state)
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
                or lease._check_hooks is not value['private_code_check']
                or code_identity(value['raw_handle'])!=value['raw_identity']):
            fail(value,'owned immutable raw-reader code lease changed')
        code_check(lease)

    def check(value,require_creator=True):
        value['full_checks']+=1
        try:
            route_check(value,require_creator)
            return original_check(value,require_creator)
        except BaseException as error:
            if value['failure'] is None:
                value['failure']=describe(error)
            raise

    def frontier(value,names,*,route=True):
        value['frontier_checks']+=1
        if route:route_check(value)
        for name in names:
            cls,fn,instructions,defaults,keywords=proxy_frontier[name]
            if (vars(cls).get(name) is not fn or fn.__code__ is not instructions
                    or fn.__defaults__ is not defaults or fn.__kwdefaults__ is not keywords):
                fail(value,'bounded stable-read next proxy dispatch changed')

    def proxy_row(proxy,*,validate=True,light=False):
        p=proxies.get(id(proxy))
        if p is None or p['proxy'] is not proxy:raise ValueError('original active bounded-read stream required')
        if validate:
            if light:
                p['entry']['light_checks']+=1
                frontier(p['entry'],('fileno','read','__exit__'))
            else:check(p['entry'])
        if p['closed']:fail(p['entry'],'closed bounded stable-read stream')
        return p

    def forget(p):
        p['closed']=True;p['entry']['streams'].remove(p);proxies.pop(id(p.get('proxy')),None)

    def close_owned(p):
        if p['closed']:return None
        p['entry']['stream_close_attempts']+=1
        try:
            closer=p['close']
            if closer is None:closer=p['stream'].close
            closer()
        except BaseException as error:
            p['entry']['stream_close_failures']+=1
            if p['entry']['failure'] is None:p['entry']['failure']='stream close failed: '+describe(error)
            return error
        forget(p)
        return None

    class Proxy:
        __slots__=()
        def __init__(self,record):record['proxy']=self;proxies[id(self)]=record
        def __enter__(self):
            p=proxy_row(self,validate=False)
            try:
                proxy_row(self,light=True)
                if p['stage']!='opened':fail(p['entry'],'bounded stable-read stream enter order changed')
                p['reader']=p['stream'].__enter__()
                frontier(p['entry'],('fileno','read','__exit__'),route=False)
                p['stage']='entered'
                return self
            except BaseException as error:
                secondary=close_owned(p)
                if secondary is not None:note(error,'stable-read enter cleanup: '+describe(secondary))
                raise
        def fileno(self):
            p=proxy_row(self,validate=False)
            if p['stage']=='entered':
                p=proxy_row(self,light=True);next_stage='first_fileno'
            elif p['stage']=='read_completed':
                p=proxy_row(self,light=True);next_stage='second_fileno'
            else:fail(p['entry'],'bounded stable-read stream fileno order changed')
            result=p['reader'].fileno()
            frontier(p['entry'],('read','fileno','__exit__') if next_stage=='first_fileno' else ('__exit__',),route=False)
            p['stage']=next_stage;return result
        def read(self,n=-1):
            p=proxy_row(self,light=True);value=p['entry']
            if p['stage']!='first_fileno':fail(value,'bounded stable-read stream read order changed')
            if type(n) is int and n==p['original_n']:
                p['stage']='reading'
                value['attempts']+=1;value['original_requested_bytes']+=n
                value['actual_requested_bytes']+=p['bounded_n']
                try:result=p['reader'].read(p['bounded_n'])
                except BaseException:value['failed_reads']+=1;p['stage']='read_failed';raise
                value['hits']+=1;p['stage']='read_completed'
                frontier(value,('fileno','__exit__'),route=False)
                return result
            value['other_read_calls']+=1
            return p['reader'].read(n)
        def __exit__(self,kind,error,tb):
            p=proxy_row(self,validate=False)
            failure=None
            try:
                try:
                    frontier(p['entry'],('__exit__',))
                    if error is None and p['stage']!='second_fileno':
                        fail(p['entry'],'incomplete bounded stable-read stream at exit')
                except BaseException as secondary:failure=secondary
                stream_failure=None
                try:result=p['stream'].__exit__(kind,error,tb)
                except BaseException as secondary:stream_failure=secondary
                close_failure=close_owned(p)
                if close_failure is not None:
                    if stream_failure is not None:note(stream_failure,'stable-read stream close: '+describe(close_failure))
                    elif error is not None:note(error,'stable-read stream close: '+describe(close_failure))
                    elif failure is None:failure=close_failure
                    else:note(failure,'stable-read stream close: '+describe(close_failure))
                try:check(p['entry'])
                except BaseException as secondary:
                    if failure is None and stream_failure is not None:
                        note(stream_failure,'stable-read terminal self-check: '+describe(secondary))
                    elif failure is None and error is not None:
                        note(error,'stable-read terminal self-check: '+describe(secondary))
                    elif failure is None:failure=secondary
                    else:note(failure,'stable-read terminal self-check: '+describe(secondary))
                if stream_failure is not None:
                    if failure is not None and error is None:
                        note(failure,'stable-read exit cleanup: '+describe(stream_failure))
                        raise failure
                    # With an existing body error, preserve the original stream
                    # __exit__ exception semantics, adding the new guard as a note.
                    if failure is not None:note(stream_failure,'stable-read exit guard: '+describe(failure))
                    raise stream_failure
                if failure is not None:
                    if error is not None:note(error,'stable-read exit guard: '+describe(failure));return False
                    raise failure
                return result
            finally:
                # A failed close stays registered for the outer owner's retry.
                # Never turn an uncertain close into an empty closed receipt.
                pass

    class BoundedStableReadLease:
        def __init__(self,expected,*,root):
            fixed_aliases()
            normalized=[path_type(p) for p in expected]
            if len(set(normalized))!=len(normalized):
                raise ValueError('duplicate canonical stable-read code path')
            pins={path_type(p):pin for p,pin in expected.items()}
            required={raw_path:RAW_SHA256,own_path:implementation['entry_sha256'],
                code_path:implementation['code_lease_sha256']}
            if any(pins.get(path)!=pin for path,pin in required.items()):
                raise ValueError('entry, raw reader and code owner require exact held source pins')
            records[id(self)]=dict(owner=self,expected=pins,root=path_type(root),state='new',
                creator=(pid_of(),thread_of()),failure=None,streams=[],hits=0,attempts=0,failed_reads=0,
                route_checks=0,full_checks=0,light_checks=0,frontier_checks=0,
                stream_close_attempts=0,stream_close_failures=0,
                original_requested_bytes=0,actual_requested_bytes=0,other_read_calls=0,
                fallback_opens=0,code_owner=None)
        def __enter__(self):
            fixed_aliases()
            value=row(self)
            if (value['state']!='new' or active[0] is not None
                    or value['creator']!=(pid_of(),thread_of())):
                raise ValueError('single-use nonnested creating-thread stable-read entry required')
            if (sys_module.platform!='win32' or sys_module.implementation.name!='cpython'
                    or path_type.open is not open_path or path_type.read_bytes is not read_bytes
                    or io_module.open is not open_io or sys_module._getframe is not frame_of
                    or get_trace() is not None or get_profile() is not None or not code_dispatch()):
                raise ValueError('configured untraced Windows/CPython entry required')
            lease=code_type(value['expected'],root=value['root'])
            value['code_owner']=lease
            private_release=make_method(release,lease);lease._release=private_release
            private_check=make_method(private_code_check,lease);lease._check_hooks=private_check
            value.update(release=private_release,private_code_check=private_check)
            try:
                enter_code(lease)
                if path_type.open is not open_path:
                    raise ValueError('Path.open changed during owned entry acquisition')
                handle=lease._files[raw_path]
                value.update(code_wrapper=lease._cached_read,handles=tuple(lease._handles),
                    raw_handle=handle,raw_identity=code_identity(handle))
                def opening(path,*args,**kwargs):
                    frame=frame_of(1)
                    try:
                        target=frame.f_code is raw_code and frame.f_globals is raw_globals
                        if target:check(value)
                        else:route_check(value,require_creator=False)
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
                        p=dict(entry=value,stream=stream,reader=stream,close=None,closed=False,stage='opened',
                            original_n=cap+1,bounded_n=before[2]+1)
                        value['streams'].append(p)
                        try:
                            p['close']=stream.close
                            frontier(value,('__init__','__enter__','fileno','read','__exit__'),route=False)
                            return Proxy(p)
                        except BaseException as error:
                            secondary=close_owned(p)
                            if secondary is not None:note(error,'stable-read post-open cleanup: '+describe(secondary))
                            raise
                    finally:del frame
                value['wrapper']=opening
                value.update(wrapper_code=opening.__code__,wrapper_defaults=opening.__defaults__,
                    wrapper_keywords=opening.__kwdefaults__,wrapper_closure=tuple(
                        (id(cell),id(cell.cell_contents)) for cell in opening.__closure__ or ()))
                active[0]=value;value['state']='active';path_type.open=opening
                check(value)
                return self
            except BaseException as error:
                failures=[]
                try:
                    if path_type.open is value.get('wrapper'):path_type.open=open_path
                except BaseException as secondary:failures.append(secondary)
                active[0]=None;value['state']='closed'
                try:
                    if lease._state=='active':exit_code(lease,type(error),error,error.__traceback__)
                except BaseException as secondary:failures.append(secondary)
                if value['failure'] is None:value['failure']=describe(error)
                value['cleanup_errors']=[describe(item) for item in failures]
                for secondary in failures:note(error,'stable-read setup cleanup: '+describe(secondary))
                raise
        def receipt(self):
            value=row(self);check(value)
            return dict(implementation,exact_stable_read_calls=value['hits'],
                exact_stable_read_attempts=value['attempts'],failed_underlying_reads=value['failed_reads'],
                counts_cover_underlying_read_return_only=True,
                route_checks=value['route_checks'],full_checks=value['full_checks'],light_checks=value['light_checks'],
                frontier_checks=value['frontier_checks'],
                stream_close_attempts=value['stream_close_attempts'],stream_close_failures=value['stream_close_failures'],
                original_requested_bytes=value['original_requested_bytes'],
                actual_requested_bytes=value['actual_requested_bytes'],
                other_read_calls=value['other_read_calls'],fallback_opens=value['fallback_opens'],
                active_streams=len(value['streams']),first_failure=value['failure'],
                code_lease=code_receipt(value['code_owner']),
                formal_result=False,formal_execution_ready=False,resource_admission=False,
                native_execution_authorized=False)
        def __exit__(self,kind,error,tb):
            value=row(self)
            if value['creator']!=(pid_of(),thread_of()):
                raise ValueError('stable-read cleanup requires creating thread')
            if value['state']=='closed':return False
            failures=[]
            try:check(value)
            except BaseException as failure:failures.append(failure)
            if value['streams']:
                failures.append(ValueError('active bounded stable-read stream at entry exit'))
                for p in tuple(value['streams']):
                    failure=close_owned(p)
                    if failure is not None:failures.append(failure)
            if path_type.open is value.get('wrapper'):path_type.open=open_path
            else:failures.append(ValueError('foreign Path.open replacement retained during cleanup'))
            try:exit_code(value['code_owner'],kind,error,tb)
            except BaseException as failure:failures.append(failure)
            finally:value['state']='closed';active[0]=None;value['cleanup_errors']=[describe(item) for item in failures]
            if failures:
                if value['failure'] is None:value['failure']=describe(failures[0])
                if error is not None:
                    for failure in failures:note(error,'bounded stable-read cleanup: '+describe(failure))
                else:
                    for failure in failures[1:]:note(failures[0],'additional cleanup: '+describe(failure))
                    raise failures[0]
            return False
        def closed_receipt(self):
            value=row(self)
            if value['state']!='closed':raise ValueError('closed stable-read entry required')
            lease=value['code_owner']
            return dict(implementation,state='closed',first_failure=value['failure'],
                code_owner_closed=lease is None or lease._state=='closed',
                remaining_code_handles=0 if lease is None else len(lease._handles),
                remaining_streams=len(value['streams']),remaining_proxies=sum(
                    p['entry'] is value for p in proxies.values()),
                stream_close_attempts=value['stream_close_attempts'],stream_close_failures=value['stream_close_failures'],
                path_open_restored=path_type.open is open_path,
                path_read_bytes_restored=path_type.read_bytes is read_bytes,
                cleanup_errors=list(value.get('cleanup_errors',())),
                formal_result=False,resource_admission=False,native_execution_authorized=False)
    entry_methods=tuple((BoundedStableReadLease,name,method_state(fn))
        for name,fn in vars(BoundedStableReadLease).items() if type(fn) is types.FunctionType)
    proxy_methods=tuple((Proxy,name,method_state(fn))
        for name,fn in vars(Proxy).items() if type(fn) is types.FunctionType)
    proxy_frontier={name:(Proxy,fn,fn.__code__,fn.__defaults__,fn.__kwdefaults__)
        for name,fn in vars(Proxy).items() if type(fn) is types.FunctionType}
    return BoundedStableReadLease


BoundedStableReadLease=_bind()
del _bind
