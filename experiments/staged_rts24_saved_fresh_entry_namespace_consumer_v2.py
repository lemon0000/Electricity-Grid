"""Conditional-TCB ENTRY initialization and local continuity; no role authority."""
import builtins
import dataclasses
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from threading import get_ident
from types import (ModuleType,FunctionType,CodeType,CellType,MappingProxyType,
                   GetSetDescriptorType,MemberDescriptorType,BuiltinFunctionType,
                   WrapperDescriptorType,MethodDescriptorType,MethodWrapperType)

ACTUAL_NAME='experiments.staged_rts24_saved_fresh_adoption_v1'
REFERENCE_NAME='_saved_F_entry_reference_v1'
ENTRY='experiments/staged_rts24_saved_fresh_adoption_v1.py'
ROOT=Path('D:/CUHKSZ/Research Project/electricity-grid')
_PATH_TYPE=type(ROOT)
_EXTERNAL_VALUE_TYPES=(BuiltinFunctionType,WrapperDescriptorType,MethodDescriptorType,MethodWrapperType)
_INPUT_TYPE=globals().get('_INPUT_TYPE')
_RUNTIME_TYPE=globals().get('_RUNTIME_TYPE')
_ABSENT=object()
_SENTINELS=tuple(getattr(dataclasses,n) for n in ('MISSING','KW_ONLY','_HAS_DEFAULT_FACTORY','_FIELD','_FIELD_CLASSVAR','_FIELD_INITVAR'))

def require(value,message):
    if not value:raise ValueError(message)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return (len(raw),sha256(raw).hexdigest())
_GRAPH_ROOTS=(type,id,len,tuple,dict,list,Ellipsis,bytes,str,int,float,bool,complex,set,frozenset,staticmethod,classmethod,property,sorted,any,ValueError,ModuleType,FunctionType,CodeType,CellType,MappingProxyType,GetSetDescriptorType,MemberDescriptorType,vars,dataclasses.Field,dataclasses._DataclassParams,dataclasses.InitVar,_PATH_TYPE,_EXTERNAL_VALUE_TYPES,_SENTINELS,json.dumps,sha256,object.__getattribute__)

def freeze_namespace_graph(module,_roots=_GRAPH_ROOTS):
    (type,id,len,tuple,dict,list,Ellipsis,bytes,str,int,float,bool,complex,set,frozenset,staticmethod,classmethod,property,sorted,any,ValueError,ModuleType,FunctionType,CodeType,CellType,MappingProxyType,GetSetDescriptorType,MemberDescriptorType,vars,Field,Params,InitVar,_PATH_TYPE,_EXTERNAL_VALUE_TYPES,_SENTINELS,dumps,sha256,getattribute)=_roots
    def require(value,message):
        if not value:raise ValueError(message)
    def canonical(value):return dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    def code_token(code):
        def const(value):
            if type(value) is CodeType:return ('code',code_token(value))
            if type(value) is bytes:return ('bytes',value.hex())
            if type(value) in (tuple,frozenset):
                rows=[const(v) for v in value]
                return (type(value).__name__,sorted(rows,key=canonical) if type(value) is frozenset else rows)
            if value is Ellipsis:return ('ellipsis',)
            require(value is None or type(value) in (str,int,float,bool,complex),'unsupported compiled constant')
            return ('complex',value.real,value.imag) if type(value) is complex else (type(value).__name__,value)
        return sha256(canonical((code.co_argcount,code.co_posonlyargcount,code.co_kwonlyargcount,code.co_nlocals,
            code.co_stacksize,code.co_flags,code.co_code.hex(),[const(v) for v in code.co_consts],code.co_names,
            code.co_varnames,code.co_filename,code.co_name,code.co_qualname,code.co_firstlineno,code.co_linetable.hex(),
            code.co_exceptiontable.hex(),code.co_freevars,code.co_cellvars))).hexdigest()

    require(type(module) is ModuleType,'exact ENTRY module required')
    namespace=module.__dict__;module_name=module.__name__
    seen={id(namespace):0};objects=[namespace];nodes=[None];code_cache={}
    def key(value):
        require(value is None or type(value) in (str,int,bool,float,bytes),'unsupported namespace mapping key')
        return canonical((type(value).__name__,value.hex() if type(value) is bytes else value))

    def external(value):return ('external',id(type(value)),id(value))

    def visit(value,depth=0):
        require(depth<=256,'namespace graph depth cap')
        typ=type(value)
        if value is None or typ in (str,int,float,bool):return ('atom',typ.__name__,value)
        if typ is bytes:return ('bytes',value.hex())
        if value is Ellipsis:return ('ellipsis',)
        if any(value is item for item in _SENTINELS):return external(value)
        if typ is ModuleType:return external(value)
        if typ is type and value.__module__!=module_name:return external(value)
        if typ is FunctionType and value.__globals__ is not namespace and value.__closure__ is None:return external(value)
        if typ not in (dict,tuple,list,set,frozenset,FunctionType,CodeType,CellType,MappingProxyType,type,
                staticmethod,classmethod,property,GetSetDescriptorType,MemberDescriptorType,
                Field,Params,InitVar,_PATH_TYPE):
            require(typ in _EXTERNAL_VALUE_TYPES,'unsupported namespace value')
            return external(value)
        identity=id(value)
        if identity in seen:return ('ref',seen[identity])
        require(len(nodes)<50000,'namespace graph node cap')
        index=len(nodes);seen[identity]=index;objects.append(value);nodes.append(None)
        def edge(v):return visit(v,depth+1)
        def mapping(v):return tuple((edge(k),edge(x)) for k,x in sorted(v.items(),key=lambda kv:key(kv[0])))
        if typ in (tuple,list):row=(typ.__name__,tuple(edge(v) for v in value))
        elif typ in (set,frozenset):row=(typ.__name__,tuple(edge(v) for v in sorted(value,key=key)))
        elif typ in (dict,MappingProxyType):row=(typ.__name__,mapping(value))
        elif typ is _PATH_TYPE:row=('path',id(typ),str(value))
        elif typ is CodeType:
            if identity not in code_cache:code_cache[identity]=code_token(value)
            row=('code',code_cache[identity])
        elif typ is FunctionType:
            own=value.__globals__ is namespace
            row=('function',value.__name__,value.__qualname__,value.__module__,
                'OWN_GLOBALS' if own else id(value.__globals__),edge(value.__code__),edge(value.__defaults__),
                edge(value.__kwdefaults__),edge(value.__closure__),edge(value.__annotations__),edge(value.__dict__))
        elif typ is CellType:
            try:contents=value.cell_contents
            except ValueError:row=('empty_cell',)
            else:row=('cell',edge(contents))
        elif typ is type:
            attrs=vars(value)
            row=('class',value.__name__,value.__qualname__,edge(value.__bases__),tuple((k,edge(v)) for k,v in sorted(attrs.items())))
        elif typ in (staticmethod,classmethod):row=(typ.__name__,edge(value.__func__),edge(value.__dict__))
        elif typ is property:row=('property',edge(value.fget),edge(value.fset),edge(value.fdel),edge(value.__doc__))
        elif typ in (GetSetDescriptorType,MemberDescriptorType):row=(typ.__name__,value.__name__,edge(value.__objclass__),edge(value.__doc__))
        else:
            fields=typ.__slots__;fields=(fields,) if type(fields) is str else tuple(fields)
            row=('dataclass_metadata',id(typ),tuple((name,edge(getattribute(value,name))) for name in fields))
        nodes[index]=row;return ('ref',index)

    excluded={'__name__','__spec__','__loader__','__builtins__'}
    nodes[0]=('namespace',tuple((k,visit(v,1)) for k,v in sorted(namespace.items()) if k not in excluded))
    return tuple(nodes),tuple(objects)

_TRACE_WRITE=sys.stderr.buffer.write
_TRACE_FLUSH=sys.stderr.buffer.flush
_TRACE_CLOCK=__import__('time').perf_counter
_TRACE_DUMPS=json.dumps

_GRAPH_STATS={'calls':0}

def timed_namespace_graph(module, _reader_code=freeze_namespace_graph.__code__, _fn=FunctionType, _ctx=globals(), _reader_defs=freeze_namespace_graph.__defaults__, _clock=_TRACE_CLOCK, _write=_TRACE_WRITE, _flush=_TRACE_FLUSH, _dumps=_TRACE_DUMPS, _base=BaseException, _stats=_GRAPH_STATS):
    typ, length, reject = (_reader_defs[0][0], _reader_defs[0][2], _reader_defs[0][20])
    count = _stats['calls']
    if typ(count) is not _reader_defs[0][9] or not 0 <= count < 40:
        raise reject('diagnostic graph call cap')
    seq = count + 1
    _stats['calls'] = seq
    kind = 'adapter' if module.__name__ == 'src.staged_rts24_saved_fresh_adoption_v1' else 'namespace'
    _write((_dumps(('graph', seq, kind, 'enter', _clock()), separators=(',', ':')) + '\n').encode('ascii'))
    _flush()
    primary = None
    sizes = (None, None, None)
    try:
        image, objects = _fn(_reader_code, _ctx, 'held_original_graph', _reader_defs)(module)
        raw = _dumps(image, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
        if length(raw) > 4194304:
            raise reject('diagnostic graph image cap')
        sizes = (length(image), length(objects), length(raw))
        return (image, objects)
    except _base as error:
        primary = error
        raise
    finally:
        try:
            _write((_dumps(('graph', seq, kind, 'exit', _clock(), *sizes), separators=(',', ':')) + '\n').encode('ascii'))
            _flush()
        except _base as output_error:
            if primary is None:
                raise
            raise primary from output_error

class NamespaceGraph:
    def __init__(self,module,_type=type,_module_type=ModuleType):
        if _type(module) is not _module_type:raise ValueError('exact ENTRY module required')
        self.module=module
    def freeze(self,_code=timed_namespace_graph.__code__,_fn=FunctionType,_ctx=globals(),_defs=timed_namespace_graph.__defaults__):
        return _fn(_code,_ctx,'held_namespace_graph',_defs)(self.module)


class NamespaceConstructionFailed(RuntimeError):
    def __init__(self,owner,primary,secondary):
        self.owner,self.primary,self.secondary=owner,primary,tuple(secondary)
        super().__init__('ENTRY namespace construction failed')
    def __reduce__(self):raise TypeError('namespace failure retains local owner')

def make_namespace_failure(owner,primary,secondary,_class=NamespaceConstructionFailed,_new=RuntimeError.__new__,
        _init=RuntimeError.__init__,_getdict=object.__getattribute__,_tuple=tuple):
    error=_new(_class);_init(error,'ENTRY namespace construction failed')
    state=_getdict(error,'__dict__');state.update(owner=owner,primary=primary,secondary=_tuple(secondary));return error

def capture_helper_bindings():
    namespace=globals();rows=[]
    for name,value in tuple(namespace.items()):
        fn=value if type(value) is FunctionType else None
        rows.append((namespace,name,value,None if fn is None else (fn.__code__,fn.__defaults__,fn.__kwdefaults__,fn.__closure__)))
    rows.append((namespace,'keyset',tuple(sorted(namespace)),'keyset'))
    for cls in (NamespaceGraph,NamespaceConstructionFailed,LiveEntryNamespace):
        for name,value in vars(cls).items():
            fn=value if type(value) is FunctionType else None
            rows.append((cls,name,value,None if fn is None else (fn.__code__,fn.__defaults__,fn.__kwdefaults__,fn.__closure__)))
            if type(value) is staticmethod:
                fn=value.__func__;rows.append((value,'__func__',fn,(fn.__code__,fn.__defaults__,fn.__kwdefaults__,fn.__closure__)))
    rows.extend((builtins,name,value,None) for name,value in tuple(vars(builtins).items()))
    rows.append((vars(builtins),'keyset',tuple(sorted(vars(builtins))),'keyset'))
    for module,names in (
        (sys,('modules','audit')),(os,('getpid',)),(object,('__setattr__',))):
        rows.extend((module,name,getattr(module,name),None) for name in names)
    return tuple(rows)

def verify_helper_bindings(rows,_get=getattr,_vars=vars,_typ=type,_error=ValueError,_tuple=tuple,_sorted=sorted):
    for namespace,name,value,metadata in rows:
        if metadata=='keyset':
            if _tuple(_sorted(namespace))!=value:raise _error('namespace helper keys changed')
            continue
        current=namespace.get(name) if _typ(namespace) is dict else _vars(namespace).get(name) if _typ(namespace) is type else _get(namespace,name)
        if current is not value:raise _error('namespace helper binding changed')
        if metadata is not None and not (value.__code__ is metadata[0] and value.__defaults__ is metadata[1]
            and value.__kwdefaults__ is metadata[2] and value.__closure__ is metadata[3]):raise _error('namespace helper callable changed')

def owner_image(owner,_id=id,_tuple=tuple):
    return _tuple(_id(value) for value in (owner._inputs,owner.module,owner.reference,owner._unit,owner._raw,
        owner._expected,owner._objects,owner._input_type,owner._builtins,owner._bindings,owner._modules,
        owner._input_entry,owner._input_close,owner._exact_type,owner._aliases,owner._fault,owner._graph_type,owner._metadata_function,owner._graph_plan))+(owner._creator,owner._phase,owner._reference_registered,owner._exec_attempts,owner._exec_completed,owner._actual_initialized)

def verify_namespace(owner,_getpid=os.getpid,_ident=get_ident,_type=type,_reject=ValueError,
        _bind_code=verify_helper_bindings.__code__,_fn=FunctionType,_ctx=globals(),_defs=verify_helper_bindings.__defaults__,
        _any=any,_tuple=tuple,_len=len,_all=all,_zip=zip,_absent=_ABSENT,_image_code=owner_image.__code__,_image_defs=owner_image.__defaults__):
    _fn(_bind_code,_ctx,'held_helper_bookend',_defs)(owner._bindings)
    if _type(owner) is not owner._exact_type or owner._seal!=_fn(_image_code,_ctx,'held_namespace_owner_image',_image_defs)(owner):raise _reject('namespace ownership fields changed')
    if owner._creator!=(_getpid(),_ident()) or owner._phase!='LIVE':raise _reject('original live namespace creator required')
    if _type(owner._inputs) is not owner._input_type:raise _reject('original exact live input type required')
    holder=owner._input_entry;holder[0](holder[1],holder[2],'held_input_entry',holder[3])(owner._inputs)
    _fn(_bind_code,_ctx,'held_helper_post_input_bookend',_defs)(owner._bindings)
    owner._metadata_function(owner,owner.module,owner._aliases[0])
    if owner._modules.get(owner._aliases[1],_absent) is not _absent:raise _reject('reference alias reappeared')
    if _any(v is owner.module and k!=owner._aliases[0] or v is owner.reference for k,v in _tuple(owner._modules.items())):raise _reject('extra ENTRY namespace alias')
    reader=owner._graph_plan;image,objects=reader[0](reader[1],reader[2],'held_namespace_graph',reader[3])(owner.module)
    _fn(_bind_code,_ctx,'held_helper_post_graph_bookend',_defs)(owner._bindings)
    owner._metadata_function(owner,owner.module,owner._aliases[0])
    if image!=owner._expected:raise _reject('ENTRY namespace graph changed')
    if _len(objects)!=_len(owner._objects) or not _all(a is b for a,b in _zip(objects,owner._objects)):raise _reject('ENTRY namespace object identity changed')
    return owner

class LiveEntryNamespace:
    __slots__=('_inputs','_creator','_phase','module','reference','_input_type','_builtins','_raw','_unit','_expected',
        '_objects','_seal','_bindings','_modules','_failure','_input_entry','_input_close','_exact_type','_aliases','_fault','_graph_type','_metadata_function','_graph_plan',
        '_reference_registered','_exec_attempts','_exec_completed','_actual_initialized','_runtime_peer')
    def __new__(cls,*args,**kwargs):raise TypeError('namespace requires original live inputs')
    def __setattr__(self,name,value):raise AttributeError('namespace ownership fields are frozen')
    def __delattr__(self,name):raise AttributeError('namespace ownership fields are frozen')
    def entry(self,_code=verify_namespace.__code__,_fn=FunctionType,_ctx=globals(),_defs=verify_namespace.__defaults__,
            _put=object.__setattr__,_error=BaseException,_reject=ValueError):
        if self._fault is not None:raise self._fault
        if self._phase!='LIVE':raise _reject('live namespace required')
        try:return _fn(_code,_ctx,'held_namespace_verifier',_defs)(self)
        except _error as error:
            _put(self,'_fault',error);_put(self,'_phase','FAULTED');raise
    def _metadata(self,module,name,_sys=sys,_type=type,_module_type=ModuleType,_path=str(ROOT/ENTRY),_error=ValueError):
        if _sys.modules is not self._modules or _type(module) is not _module_type or self._modules.get(name) is not module:raise _error('ENTRY namespace alias changed')
        if not (module.__name__==name and module.__file__==_path and module.__package__=='experiments'
            and module.__spec__ is None and module.__loader__ is None and module.__dict__['__builtins__'] is self._builtins):raise _error('ENTRY namespace metadata changed')
    def close(self,primary=None,_code=verify_namespace.__code__,_fn=FunctionType,_ctx=globals(),_defs=verify_namespace.__defaults__,
            _put=object.__setattr__,_sys=sys,_absent=_ABSENT,_tuple=tuple,_any=any,_error=ValueError,_failure_type=NamespaceConstructionFailed,_base=BaseException,
            _failure_code=make_namespace_failure.__code__,_failure_defs=make_namespace_failure.__defaults__,_bool=bool,
            _check_code=verify_helper_bindings.__code__,_check_defs=verify_helper_bindings.__defaults__):
        if self._phase=='CONSUMED':
            peer=self._runtime_peer
            if not (peer is not None and peer._namespace is self and peer._source is self._inputs
                and self._inputs._successor is peer and self._inputs._phase=='CONSUMED'
                and self._inputs._resource.owner is peer):raise _error('namespace runtime successor differs')
            return
        if self._phase=='CLOSED':return
        if self._phase=='UNRESOLVED':raise self._failure
        errors=[]
        if primary is None and self._fault is not None:primary=self._fault
        if self._phase=='LIVE':
            try:_fn(_code,_ctx,'held_namespace_close_bookend',_defs)(self)
            except _base as error:
                if primary is None:primary=error
                else:errors.append(('bindings',error))
        actual_name,reference_name=self._aliases
        if _sys.modules is not self._modules:errors.append(('modules_container',_error('foreign modules container retained')))
        aliases=[k for k,v in _tuple(self._modules.items()) if (self.module is not None and v is self.module and k!=actual_name)
            or (self.reference is not None and v is self.reference and not (self._reference_registered and k==actual_name))]
        if aliases:errors.append(('extra_alias',_error('extra ENTRY alias retained')))
        current=self._modules.get(actual_name,_absent)
        if current is not _absent:
            if current is self.module or self._reference_registered and current is self.reference:del self._modules[actual_name]
            else:errors.append(('foreign_alias',_error('foreign ENTRY alias retained')))
        if reference_name in self._modules:errors.append(('reserved_alias',_error('foreign reserved reference alias retained')))
        holder=self._input_close
        try:holder[0](holder[1],holder[2],'held_inputs_cleanup',holder[3])(self._inputs)
        except _base as error:errors.append(('inputs_cleanup',error))
        try:_fn(_check_code,_ctx,'held_post_cleanup_bookend',_check_defs)(self._bindings)
        except _base as error:errors.append(('post_cleanup_bindings',error))
        failed=primary is not None or _bool(errors) or _any(self._inputs._resource.pending)
        _put(self,'_phase','UNRESOLVED' if failed else 'CLOSED')
        if failed:
            failure=_fn(_failure_code,_ctx,'held_namespace_failure',_failure_defs)(self,primary,errors)
            _put(self,'_failure',failure);raise failure from primary
    def __reduce__(self):raise TypeError('live namespace cannot be serialized')
    def __copy__(self):raise TypeError('live namespace cannot be copied')
    def __deepcopy__(self,memo):raise TypeError('live namespace cannot be copied')
    def transfer_runtime(self):
        self.entry()
        specs=tuple((FunctionType,fn.__code__,globals(),fn.__defaults__) for fn in
            (prepare_runtime_namespace,verify_runtime_namespace,close_runtime_namespace))
        transfer=type(self._inputs).transfer_runtime
        held=(FunctionType,transfer.__code__,transfer.__globals__,transfer.__defaults__)
        try:return held[0](held[1],held[2],'held_core_runtime_transfer',held[3])(self._inputs,self,specs)
        except BaseException as error:
            if self._runtime_peer is None:
                object.__setattr__(self,'_fault',error);object.__setattr__(self,'_phase','FAULTED')
            raise


def runtime_namespace_image(namespace,runtime,_id=id,_tuple=tuple):
    return _tuple(_id(value) for value in (namespace,namespace._inputs,namespace.module,namespace.reference,namespace._unit,
        namespace._raw,namespace._expected,namespace._objects,namespace._bindings,namespace._modules,namespace._builtins,
        namespace._graph_plan,namespace._seal,namespace._aliases,namespace._metadata_function,namespace._input_entry,namespace._input_close,
        namespace._exact_type,namespace._input_type,namespace._graph_type,namespace._fault,runtime))+(namespace._creator,
        namespace._exec_attempts,namespace._exec_completed,namespace._actual_initialized,namespace._reference_registered)


def prepare_runtime_namespace(namespace,runtime,_runtime_type=_RUNTIME_TYPE):
    namespace.entry()
    require(_runtime_type is not None and type(runtime) is _runtime_type and runtime._source is namespace._inputs
        and runtime._namespace is namespace and namespace._runtime_peer is None,'exact prepared runtime receiver required')
    return runtime_namespace_image(namespace,runtime)


def verify_runtime_namespace(namespace,runtime,_runtime_type=_RUNTIME_TYPE,_fn=FunctionType,_ctx=globals(),
        _check_code=verify_helper_bindings.__code__,_check_defs=verify_helper_bindings.__defaults__,
        _image_code=runtime_namespace_image.__code__,_image_defs=runtime_namespace_image.__defaults__,_reject=ValueError,
        _type=type,_len=len,_all=all,_zip=zip):
    _fn(_check_code,_ctx,'held_consumed_namespace_helper',_check_defs)(namespace._bindings)
    if not (_runtime_type is not None and _type(runtime) is _runtime_type and namespace._phase=='CONSUMED'
        and namespace._runtime_peer is runtime and runtime._namespace is namespace and runtime._source is namespace._inputs
        and namespace._inputs._phase=='CONSUMED' and namespace._inputs._successor is runtime
        and runtime._resource.owner is runtime):raise _reject('runtime namespace successor differs')
    image=_fn(_image_code,_ctx,'held_runtime_namespace_image',_image_defs)(namespace,runtime)
    if image!=runtime._namespace_snapshot:raise _reject('consumed namespace immutable fields changed')
    metadata=namespace._metadata_function
    _fn(metadata.__code__,_ctx,'held_consumed_namespace_metadata',metadata.__defaults__)(namespace,namespace.module,namespace._aliases[0])
    reader=namespace._graph_plan;actual,objects=reader[0](reader[1],reader[2],'held_runtime_namespace_graph',reader[3])(namespace.module)
    _fn(_check_code,_ctx,'held_runtime_namespace_post_graph',_check_defs)(namespace._bindings)
    if actual!=namespace._expected or _len(objects)!=_len(namespace._objects) or not _all(a is b for a,b in _zip(objects,namespace._objects)):
        raise _reject('runtime namespace graph or identity changed')
    return namespace


def close_runtime_namespace(namespace,runtime,_sys=sys,_absent=_ABSENT,_error=ValueError,_tuple=tuple,
        _fn=FunctionType,_ctx=globals(),_code=verify_runtime_namespace.__code__,_defs=verify_runtime_namespace.__defaults__):
    _fn(_code,_ctx,'held_runtime_namespace_cleanup_bookend',_defs)(namespace,runtime)
    if not (namespace._runtime_peer is runtime and runtime._namespace is namespace and namespace._phase=='CONSUMED'):raise _error('namespace cleanup runtime owner differs')
    errors=[];name=namespace._aliases[0];modules=namespace._modules
    if _sys.modules is not modules:errors.append('modules_container')
    extra=[key for key,value in _tuple(modules.items()) if value is namespace.module and key!=name or value is namespace.reference]
    if extra:errors.append('extra_alias')
    actual=modules.get(name,_absent)
    if actual is namespace.module:del modules[name]
    elif actual is not _absent:errors.append('foreign_alias')
    if errors:raise _error('runtime namespace cleanup unresolved: '+','.join(errors))

def consumer_root(module,name,relative,raw):
    path=ROOT/relative;namespace=vars(module)
    require(type(module) is ModuleType and sys.modules.get(relative[:-3].replace('/','.')) is module
        and type(module.__file__) is str and Path(module.__file__).absolute()==path,'canonical consumer source module required')
    unit=compile(raw,str(path),'exec',dont_inherit=True,optimize=0)
    codes=[code for code in unit.co_consts if type(code) is CodeType and code.co_name==name]
    require(len(codes)==1,'fixed consumer compiled source root required')
    fn=namespace.get(name)
    require(type(fn) is FunctionType and fn.__globals__ is namespace and fn.__code__==codes[0]
        and fn.__closure__ is None,'compiled consumer root differs')
    if relative=='src/staged_rts24_development_v1.py' and name=='load_fixture':
        config=namespace.get('CONFIG');expected=ROOT/'configs/staged_deliverability_rts24_v1.DRAFT.yaml'
        require(type(config) is _PATH_TYPE and str(config)==str(expected) and type(fn.__defaults__) is tuple
            and len(fn.__defaults__)==1 and fn.__defaults__[0] is config and fn.__kwdefaults__ is None,
            'fixed original CONFIG default required')
    else:
        if name=='read_bytes':
            require(type(fn.__defaults__) is tuple and len(fn.__defaults__)==1 and fn.__defaults__[0] is False,
                'exact consumer False default required')
        elif name=='bookend':
            require(fn.__defaults__ is None and type(fn.__kwdefaults__) is dict
                and set(fn.__kwdefaults__)=={'inventory'} and fn.__kwdefaults__['inventory'] is True,'exact full bookend default required')
        else:require(fn.__defaults__ is fn.__kwdefaults__ is None,'consumer empty defaults required')
    return (module,name,fn,fn.__code__,fn.__defaults__,fn.__kwdefaults__,canonical(fn.__kwdefaults__),
        fn.__closure__,namespace,relative)


def consumer_helper_checker(owner):
    context=owner._namespace_specs[1][2]
    rows=[row for row in owner._namespace._bindings if row[0] is context and row[1]=='verify_helper_bindings']
    require(len(rows)==1,'original consumer helper checker required')
    row=rows[0];require(type(row[3]) is tuple,'held helper checker metadata required')
    return FunctionType(row[3][0],context,'held_consumer_helper_bookend',row[3][1])


def prepare_consumer_plan(owner):
    checker=consumer_helper_checker(owner);checker(owner._namespace._bindings)
    primary=None;plan=None
    try:plan=build_consumer_plan(owner)
    except BaseException as error:primary=error
    finally:
        try:checker(owner._namespace._bindings)
        except BaseException as error:
            if primary is not None:raise primary from error
            raise
    if primary is not None:raise primary
    return plan


def build_consumer_plan(owner):
    require(type(owner) is _RUNTIME_TYPE and owner._phase=='IMPORTING' and owner._adapter is None
        and owner._consumer_plan is None and owner._consume_state is None,'original pre-LIVE consumer owner required')
    boundary=owner._boundary;spec=owner._boundary_phase
    require(spec[0](spec[1],spec[2],'held_consumer_boundary',spec[3])(boundary)=='CLOSED'
        and boundary._adapter is not None and len(boundary._runtime_bindings)==14 and boundary._retention,
        'completed closed import proof required before consumer preparation')
    namespace=owner._namespace;raw=dict(owner._sources);adapter=boundary._adapter
    consumer=consumer_root(namespace.module,'_expectation_binding_entry',ENTRY,raw[ENTRY])
    roots=[(adapter,name,'src/staged_rts24_saved_fresh_adoption_v1.py')
        for name in ('hold','capture','bookend','caller_image','sources','validate_metrics')]
    roots.extend(((adapter.core,'load_fixture','src/staged_rts24_development_v1.py'),
        (adapter.mechanical,'inventory','src/staged_rts24_p2_package_check_v1.py'),
        (adapter.codec,'read_bytes','src/staged_rts24_evidence_store_v1.py'),
        (adapter.prefix.point,'_outer','src/staged_rts24_saved_point_replay_v1.py')))
    rows=tuple(consumer_root(module,name,path,raw[path]) for module,name,path in roots)
    bindings=tuple((row[0],row[1],row[2],row[3],row[4],row[6]) for row in rows)
    edges=((adapter,'core',adapter.core),(adapter,'mechanical',adapter.mechanical),(adapter,'codec',adapter.codec),
        (adapter,'prefix',adapter.prefix),(adapter.prefix,'point',adapter.prefix.point),
        (adapter.core,'CONFIG',adapter.core.CONFIG),(adapter.core,'ROOT',adapter.core.ROOT))
    require(type(adapter.core.ROOT) is _PATH_TYPE and str(adapter.core.ROOT)==str(ROOT),'fixed consumer core ROOT required')
    source_pins=tuple((path,pin(raw[path])) for path in (ENTRY,)+tuple(dict.fromkeys(row[9] for row in rows)))
    plan=(owner,owner._creator,namespace,boundary,adapter,boundary._retention,consumer,rows,(adapter,bindings),edges,
        source_pins,'expectation_binding',b'{"consumer":"expectation_binding","v":1}')
    verify_consumer_plan(owner,plan)
    return plan


def verify_consumer_plan(owner,plan):
    require(type(owner) is _RUNTIME_TYPE and type(plan) is tuple and len(plan)==13,'closed consumer plan required')
    original,creator,namespace,boundary,adapter,retention,consumer,rows,binding,edges,source_pins,consumer_id,request=plan
    require(original is owner and creator==owner._creator and creator[:2]==(os.getpid(),get_ident())
        and namespace is owner._namespace and namespace._runtime_peer is owner and boundary is owner._boundary
        and owner._resource.owner is owner and owner._resource.phase=='LIVE','same process/thread/native consumer owner required')
    require(owner._phase in ('IMPORTING','LIVE'),'active consumer lifecycle required')
    if owner._consumer_plan is None:
        require(owner._phase=='IMPORTING' and owner._consume_state is None,'only uncommitted IMPORTING plan permitted')
    else:
        require(owner._consumer_plan is plan and owner._consume_state in ('PREPARED','RUNNING','CONSUMED','FAILED'),
            'consumer plan commitment or lifecycle changed')
    require(boundary._adapter is adapter and boundary._retention is retention and type(retention) is tuple
        and retention and all(sys.modules.get(name) is module for name,module in retention),'original consumer retention required')
    if owner._phase=='LIVE':
        require(owner._adapter is adapter and owner._retention is retention and owner._import_profile_matched
            and owner._adapter_bindings is boundary._runtime_bindings,
            'consumer requires original profile-matched LIVE adapter')
    require(type(rows) is tuple and len(rows)==10 and type(edges) is tuple and len(edges)==7
        and type(source_pins) is tuple and len(source_pins)==6,'complete consumer plan shape required')
    require(consumer_id=='expectation_binding' and type(consumer_id) is str
        and type(request) is bytes and request==b'{"consumer":"expectation_binding","v":1}','fixed consumer data request required')
    expected_roots=tuple((adapter,name,'src/staged_rts24_saved_fresh_adoption_v1.py')
        for name in ('hold','capture','bookend','caller_image','sources','validate_metrics'))+(
        (adapter.core,'load_fixture','src/staged_rts24_development_v1.py'),
        (adapter.mechanical,'inventory','src/staged_rts24_p2_package_check_v1.py'),
        (adapter.codec,'read_bytes','src/staged_rts24_evidence_store_v1.py'),
        (adapter.prefix.point,'_outer','src/staged_rts24_saved_point_replay_v1.py'))
    require(all(type(row) is tuple and len(row)==10 and row[0] is expected[0] and row[1]==expected[1]
        and row[9]==expected[2] for row,expected in zip(rows,expected_roots)),'fixed ten-member consumer manifest differs')
    expected_edges=((adapter,'core',rows[6][0]),(adapter,'mechanical',rows[7][0]),(adapter,'codec',rows[8][0]),
        (adapter,'prefix',adapter.prefix),(adapter.prefix,'point',rows[9][0]),
        (rows[6][0],'CONFIG',rows[6][4][0]),(rows[6][0],'ROOT',rows[6][0].ROOT))
    require(all(type(edge) is tuple and len(edge)==3 and edge[0] is expected[0] and edge[1]==expected[1]
        and edge[2] is expected[2] for edge,expected in zip(edges,expected_edges)),'fixed consumer edge manifest differs')
    require(type(rows[6][0].ROOT) is _PATH_TYPE and str(rows[6][0].ROOT)==str(ROOT),'fixed consumer core ROOT changed')
    held_raw=dict(owner._sources);paths=(ENTRY,)+tuple(dict.fromkeys(row[2] for row in expected_roots))
    require(source_pins==tuple((path,pin(held_raw[path])) for path in paths),'consumer held source manifest changed')
    for row in (consumer,)+rows:
        require(type(row) is tuple and len(row)==10,'immutable consumer root row required')
        module,name,fn,code,defaults,kw,kw_raw,closure,context,relative=row
        require(type(module) is ModuleType and vars(module) is context and sys.modules.get(relative[:-3].replace('/','.')) is module
            and Path(module.__file__).absolute()==ROOT/relative,'consumer module identity changed')
        require(context.get(name) is fn and type(fn) is FunctionType and fn.__globals__ is context and fn.__code__ is code
            and fn.__defaults__ is defaults and fn.__kwdefaults__ is kw and canonical(fn.__kwdefaults__)==kw_raw
            and fn.__closure__ is closure is None,'consumer callable identity or metadata changed')
    require(consumer[0] is namespace.module and consumer[1]=='_expectation_binding_entry','fixed ENTRY consumer required')
    authenticated=boundary._runtime_bindings
    require(type(authenticated) is tuple and len(authenticated)==14,'original fourteen adapter roots required')
    for row in rows[:6]:
        matches=[item for item in authenticated if item[0]==row[1]]
        require(len(matches)==1,'original adapter binding member required')
        item=matches[0]
        require(len(item)==6 and item[1] is row[2] and item[2] is row[3] and item[3] is row[4]
            and item[4]==row[6] and item[5] is row[7],'consumer adapter root lost original import identity')
    require(type(binding) is tuple and len(binding)==2 and binding[0] is adapter and type(binding[1]) is tuple
        and len(binding[1])==10,'original complete consumer binding required')
    for row,item in zip(rows,binding[1]):
        require(type(item) is tuple and len(item)==6 and all(a is b for a,b in zip(item[:5],row[:5]))
            and item[5] is row[6],'consumer binding member changed')
    for edge in edges:
        require(type(edge) is tuple and len(edge)==3 and vars(edge[0]).get(edge[1]) is edge[2],
            'consumer dependency edge changed')
    return plan


def invoke_consumer_plan(owner,consumer_id,raw_inputs):
    helper_check=consumer_helper_checker(owner);helper_check(owner._namespace._bindings)
    plan=owner._consumer_plan;verify_consumer_plan(owner,plan)
    require(owner._phase=='LIVE' and owner._consume_state=='RUNNING' and type(consumer_id) is str and consumer_id==plan[11]
        and type(raw_inputs) is bytes and raw_inputs==plan[12],'fixed one-shot consumer invocation required')
    checker=(verify_consumer_plan.__code__,verify_consumer_plan.__globals__,verify_consumer_plan.__defaults__)
    post_check=FunctionType(checker[0],checker[1],'held_post_consumer_plan',checker[2])
    primary=None;secondary=[]
    try:
        returned=plan[6][2](plan[8]);require(returned is plan[4],'ENTRY consumer returned foreign adapter')
    except BaseException as error:primary=error
    finally:
        for fn,args in ((helper_check,(owner._namespace._bindings,)),(post_check,(owner,plan))):
            try:fn(*args)
            except BaseException as error:
                if primary is None:primary=error
                else:secondary.append(error)
    if primary is not None:
        if secondary:raise primary from BaseExceptionGroup('consumer post-bookend failures',secondary)
        raise primary
    result=canonical(dict(schema='staged_saved_F_consumer_binding_result_v1',authority='DRAFT_NONAUTHORITATIVE',
        consumer='expectation_binding',binding_members=10,same_live_owner=True,consumer_return_is_adapter=True,
        external_expected_truth_verified=False,upstream_owner_verified=False,parent_independently_authenticated_python_object_graph=False,
        startup_tcb_authenticated=False,independent_root_verified=False,native_behavior_verified=False,full_runtime_binding_verified=False,
        full_P1_content_verified=False,producer_capability_verified=False,role_bootstrap=False,permit_issued=False,native_authorized=False,
        F_launch_admitted=False,actual_F=False,run_authority=False,scientific_evidence_adopted=False,resource_admission=False,
        formal_result=False,production_seal=False))
    require(len(result)<=2048,'consumer result byte cap');return result


def open_entry_namespace(inputs,expected_helper_bindings,_input_type=_INPUT_TYPE,_check_code=verify_helper_bindings.__code__,_fn=FunctionType,
        _ctx=globals(),_defs=verify_helper_bindings.__defaults__,_verify_code=verify_namespace.__code__,_verify_defs=verify_namespace.__defaults__,
        _compile=compile,_module_type=ModuleType,_vars=vars,_exec=exec,_sys=sys,_put=object.__setattr__,_base=BaseException,
        _failure_type=NamespaceConstructionFailed,_require=require,_owner_type=LiveEntryNamespace,_graph_type=NamespaceGraph,_type=type,
        _tuple_type=tuple,_reject=ValueError,_failure_code=make_namespace_failure.__code__,_failure_defs=make_namespace_failure.__defaults__,
        _graph_builder_code=timed_namespace_graph.__code__,_graph_builder_defs=timed_namespace_graph.__defaults__):
    if _type(expected_helper_bindings) is not _tuple_type:raise _reject('bootstrap-held helper bindings required')
    _fn(_check_code,_ctx,'held_initial_helper_root',_defs)(expected_helper_bindings)
    _require(_input_type is not None and type(inputs) is _input_type,'creating bootstrap exact inputs required')
    require(ACTUAL_NAME not in sys.modules and REFERENCE_NAME not in sys.modules,'ENTRY namespace aliases must be absent')
    require(sys.modules['__main__'] is not sys.modules.get(ACTUAL_NAME),'private ENTRY must differ from bootstrap main')
    owner=object.__new__(_owner_type)
    for name,value in dict(_inputs=inputs,_creator=(os.getpid(),get_ident()),_phase='OPENING',module=None,reference=None,
        _input_type=_input_type,_builtins=vars(builtins),_modules=sys.modules,_failure=None,_fault=None,_exact_type=_owner_type,_aliases=(ACTUAL_NAME,REFERENCE_NAME),
        _reference_registered=False,_exec_attempts=0,_exec_completed=0,_actual_initialized=False,_runtime_peer=None,
        _graph_type=_graph_type,_metadata_function=_owner_type._metadata,
        _graph_plan=(_fn,_graph_builder_code,_ctx,_graph_builder_defs),
        _input_entry=(FunctionType,_input_type.entry.__code__,_input_type.entry.__globals__,_input_type.entry.__defaults__),
        _input_close=(FunctionType,_input_type.close.__code__,_input_type.close.__globals__,_input_type.close.__defaults__)).items():object.__setattr__(owner,name,value)
    object.__setattr__(owner,'_bindings',expected_helper_bindings)
    held_close=(FunctionType,LiveEntryNamespace.close.__code__,globals(),LiveEntryNamespace.close.__defaults__)
    try:
        inputs.entry();_fn(_check_code,_ctx,'held_helper_pre_source_bookend',_defs)(owner._bindings)
        raw=inputs.source_bytes(ENTRY);_fn(_check_code,_ctx,'held_helper_post_source_bookend',_defs)(owner._bindings)
        _put(owner,'_raw',raw)
        unit=_compile(raw,str(ROOT/ENTRY),'exec',dont_inherit=True,optimize=0);_put(owner,'_unit',unit)
        def create(name):
            _require(_sys.modules is owner._modules and name not in owner._modules,'ENTRY alias occupied before registration')
            module=_module_type(name);module.__dict__.update(__file__=str(ROOT/ENTRY),__package__='experiments',__spec__=None,__loader__=None,__builtins__=owner._builtins)
            owner._modules[name]=module;return module
        _fn(_check_code,_ctx,'held_helper_pre_create_bookend',_defs)(owner._bindings)
        _put(owner,'reference',create(ACTUAL_NAME));_put(owner,'_reference_registered',True)
        _fn(_check_code,_ctx,'held_helper_check',_defs)(owner._bindings)
        _put(owner,'_exec_attempts',1);_exec(unit,_vars(owner.reference),_vars(owner.reference));_put(owner,'_exec_completed',1)
        _fn(_check_code,_ctx,'held_helper_check',_defs)(owner._bindings);owner._metadata_function(owner,owner.reference,ACTUAL_NAME)
        expected,_=_fn(_graph_builder_code,_ctx,'held_reference_graph',_graph_builder_defs)(owner.reference)
        _fn(_check_code,_ctx,'held_helper_post_reference_bookend',_defs)(owner._bindings)
        owner._metadata_function(owner,owner.reference,ACTUAL_NAME);del owner._modules[ACTUAL_NAME];_put(owner,'_reference_registered',False)
        _put(owner,'module',create(ACTUAL_NAME));_sys.audit('electricity_grid.namespace.registered',owner.module)
        _fn(_check_code,_ctx,'held_helper_check',_defs)(owner._bindings)
        _require(REFERENCE_NAME not in owner._modules,'reference alias occupied before actual initialization')
        _put(owner,'_exec_attempts',2);_exec(unit,_vars(owner.module),_vars(owner.module));_put(owner,'_exec_completed',2);_put(owner,'_actual_initialized',True)
        _fn(_check_code,_ctx,'held_helper_check',_defs)(owner._bindings);owner._metadata_function(owner,owner.module,ACTUAL_NAME)
        actual,objects=_fn(_graph_builder_code,_ctx,'held_actual_graph',_graph_builder_defs)(owner.module)
        _fn(_check_code,_ctx,'held_helper_post_oracle_bookend',_defs)(owner._bindings)
        require(actual==expected,'actual ENTRY differs from held-raw namespace oracle')
        for name,value in dict(_expected=expected,_objects=objects,_phase='LIVE').items():object.__setattr__(owner,name,value)
        object.__setattr__(owner,'_seal',owner_image(owner))
        return _fn(_verify_code,_ctx,'held_namespace_verify',_verify_defs)(owner)
    except _base as primary:
        try:held_close[0](held_close[1],held_close[2],'held_namespace_failure_cleanup',held_close[3])(owner,primary)
        except _failure_type:raise
        except _base as error:raise _fn(_failure_code,_ctx,'held_outer_namespace_failure',_failure_defs)(owner,primary,(error,)) from primary
        raise _fn(_failure_code,_ctx,'held_outer_namespace_failure',_failure_defs)(owner,primary,()) from primary
