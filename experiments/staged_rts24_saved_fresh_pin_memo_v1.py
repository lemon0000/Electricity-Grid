"""Call-local immutable pin derivation reuse; every original file read is retained."""
import builtins
import hashlib
import types
import ast

_SHA=hashlib.sha256
_LEN=builtins.len
_TYPE=builtins.type
_BYTES=bytes
_DICT=dict
_FUNCTION=types.FunctionType
_INT=int
_STR=str
_SET=set
_GLOBALS=globals
_VARS=vars
_REVERSED=reversed
_BASE_EXCEPTION=BaseException
_VALUE_ERROR=ValueError
_GROUP=BaseExceptionGroup
_TUPLE=tuple
_ANY=any
_NEXT=next
_COMPILE=compile
_HASHLIB=hashlib
_BUILTINS=builtins
_AST=ast
_CODE=types.CodeType
_MODULE=types.ModuleType
_ZIP=zip
_PIN_AST=ast.dump(ast.parse('def pin(raw):\n return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())\n').body[0])


def function_references(raw,filename):
    """Verification-only references; actor modules still execute their original loader."""
    tree=_AST.parse(raw)
    pin_node=_NEXT(n for n in tree.body if _TYPE(n) is _AST.FunctionDef and n.name=='pin')
    if _AST.dump(pin_node)!=_PIN_AST:raise _VALUE_ERROR('same fixed pin formula required for shared raw cache')
    code=_COMPILE(raw,_STR(filename),'exec',dont_inherit=True,optimize=0)
    result={}
    for name in ('pin','load'):
        node=_NEXT(n for n in tree.body if _TYPE(n) is _AST.FunctionDef and n.name==name)
        unit=_NEXT(n for n in code.co_consts if _TYPE(n) is _CODE and n.co_name==name)
        defaults=_TUPLE(_AST.literal_eval(n) for n in node.args.defaults) or None
        result[name]=(unit,defaults)
    result['pin_ast']=_PIN_AST
    return result


class PinMemo:
    def __init__(self,max_entries=2048,max_bytes=67108864):
        if _TYPE(max_entries) is not _INT or max_entries<0 or _TYPE(max_bytes) is not _INT or max_bytes<0:
            raise _VALUE_ERROR('exact nonnegative cache caps required')
        self._type=_TYPE;self._bytes=_BYTES;self._dict=_DICT;self._int=_INT;self._str=_STR;self._set=_SET;self._len=_LEN;self._error=_VALUE_ERROR
        self._caps=(max_entries,max_bytes)
        self._values={}
        self._resident=0
        self._calls=self._hits=self._misses=self._fallbacks=0
        self._closed=False

    def pin(self,raw,original):
        if self._closed:raise self._error('closed pin memo')
        self._calls+=1
        if self._type(raw) is not self._bytes:
            self._fallbacks+=1;self._misses+=1
            return original(raw)
        item=self._values.get(raw)
        if item is not None:
            self._hits+=1
            return {'bytes':item[0],'sha256':item[1]}
        self._misses+=1
        result=original(raw)
        if self._type(result) is not self._dict or self._set(result)!=self._set(('bytes','sha256')) or self._type(result['bytes']) is not self._int or result['bytes']!=self._len(raw) or self._type(result['sha256']) is not self._str:
            raise self._error('fixed pin result required')
        if self._len(self._values)<self._caps[0] and self._resident+self._len(raw)<=self._caps[1]:
            self._values[raw]=(result['bytes'],result['sha256'])
            self._resident+=self._len(raw)
        else:self._fallbacks+=1
        return result

    def metrics(self):
        return {'calls':self._calls,'hits':self._hits,'misses':self._misses,'fallbacks':self._fallbacks,
            'entries':self._values.__len__(),'resident_bytes':self._resident,'max_entries':self._caps[0],'max_bytes':self._caps[1],'closed':self._closed}

    def close(self):
        self._values.clear();self._resident=0;self._closed=True


class MetadataPinSession:
    """Only a fixed metadata graph may be wrapped; loaded modules remain fresh."""
    def __init__(self,references,max_entries=2048,max_bytes=67108864):
        self._references={_STR(p):_DICT(value) for p,value in references.items()}
        self.memo=PinMemo(max_entries,max_bytes)
        self._modules=[]
        self._active=False
        self._sha=_SHA;self._len=_LEN
        self._vars=_VARS;self._set=_SET;self._reversed=_REVERSED;self._base=_BASE_EXCEPTION;self._error=_VALUE_ERROR;self._group=_GROUP
        self._type=_TYPE;self._str=_STR;self._tuple=_TUPLE;self._any=_ANY;self._function=_FUNCTION;self._module=_MODULE;self._zip=_ZIP;self._globals_fn=_GLOBALS
        self._builtins=_BUILTINS;self._hashlib=_HASHLIB;self._dict=_DICT;self._bytes=_BYTES;self._int=_INT
        self._last_metrics=None
        self._helper_globals=_GLOBALS()
        names=('_SHA','_LEN','_TYPE','_BYTES','_DICT','_FUNCTION','_INT','_STR','_SET','_GLOBALS','_VARS','_REVERSED','_BASE_EXCEPTION','_VALUE_ERROR','_GROUP','_TUPLE','_ANY','_NEXT','_COMPILE','_HASHLIB','_BUILTINS','_AST','_CODE','_MODULE','_ZIP','_PIN_AST','PinMemo','MetadataPinSession','function_references','hashlib','builtins','ast','types')
        self._helper_bindings={n:self._helper_globals[n] for n in names}

    def __enter__(self):
        if self._active or self.memo._closed:raise self._error('single metadata pin session required')
        self._primitives();self._active=True;return self

    def _primitives(self):
        if self._hashlib.sha256 is not self._sha or self._builtins.len is not self._len or self._builtins.dict is not self._dict or self._builtins.type is not self._type or self._builtins.bytes is not self._bytes or self._builtins.int is not self._int or self._builtins.str is not self._str or self._builtins.set is not self._set or self._builtins.vars is not self._vars or self._builtins.reversed is not self._reversed or self._builtins.BaseException is not self._base or self._builtins.ValueError is not self._error:
            raise self._error('pin primitives changed')
        if self._any(self._helper_globals.get(n) is not value for n,value in self._helper_bindings.items()):raise self._error('pin helper globals changed')
        if self._builtins.zip is not self._zip or self._builtins.globals is not self._globals_fn or self._builtins.tuple is not self._tuple or self._builtins.any is not self._any or self._builtins.BaseExceptionGroup is not self._group:raise self._error('pin closure/cleanup primitives changed')

    def attach(self,module):
        if not self._active:raise self._error('inactive metadata pin session')
        if self._type(module) is not self._module:raise self._error('exact metadata module required')
        namespace=self._vars(module)
        expected=self._references.get(self._str(namespace.get('__file__')))
        if expected is None or expected.get('pin_ast')!=self._helper_bindings['_PIN_AST']:raise self._error('metadata module outside fixed formula graph')
        if self._any(row[0] is module for row in self._modules):raise self._error('same module attached twice')
        original_pin=namespace['pin'];original_load=namespace['load']
        if self._type(original_pin) is not self._function or self._type(original_load) is not self._function or original_pin.__globals__ is not namespace or original_load.__globals__ is not namespace:
            raise self._error('original metadata functions required')
        if namespace['sha256'] is not self._sha or 'len' in namespace or 'dict' in namespace or namespace.get('__builtins__') is not self._vars(self._builtins):
            raise self._error('fixed metadata hash globals required')
        for name,fn in (('pin',original_pin),('load',original_load)):
            if fn.__code__!=expected[name][0] or fn.__defaults__!=expected[name][1] or fn.__kwdefaults__ is not None or fn.__closure__ is not None:
                raise self._error('fixed metadata function source/defaults required')
        before=self._dict(namespace)
        def memo_pin(raw):return self.memo.pin(raw,original_pin)
        def fresh_load(*args,**kwargs):
            result=original_load(*args,**kwargs)
            return self.attach(result)
        metadata=self._tuple((fn,fn.__code__,fn.__defaults__,fn.__kwdefaults__,fn.__closure__,None if fn.__closure__ is None else self._tuple((cell,cell.cell_contents) for cell in fn.__closure__)) for fn in (original_pin,original_load,memo_pin,fresh_load))
        self._modules.append((module,before,memo_pin,fresh_load,metadata))
        namespace['pin']=memo_pin;namespace['load']=fresh_load
        return module

    def _bookend(self):
        self._primitives()
        for module,before,pin_fn,load_fn,metadata in self._modules:
            current=self._vars(module)
            if self._set(current)!=self._set(before):raise self._error('metadata global keyset changed')
            if current['pin'] is not pin_fn or current['load'] is not load_fn:raise self._error('managed metadata binding changed')
            if self._any(current[name] is not value for name,value in before.items() if name not in ('pin','load')):
                raise self._error('metadata global binding changed')
            for fn,code,defaults,kw,closure,cells in metadata:
                if fn.__code__ is not code or fn.__defaults__ is not defaults or fn.__kwdefaults__ is not kw or fn.__closure__ is not closure:
                    raise self._error('metadata function metadata changed')
                if cells is not None and self._any(cell is not original or cell.cell_contents is not value for cell,(original,value) in self._zip(fn.__closure__,cells)):
                    raise self._error('metadata wrapper closure changed')

    def __exit__(self,kind,primary,tb):
        cleanup=None
        try:self._bookend()
        except self._base as error:cleanup=error
        finally:
            try:
                self._last_metrics=self.memo.metrics()
                self._last_metrics['wrapped_modules']=self._len(self._modules)
            except self._base as error:
                if cleanup is None:cleanup=error
            finally:
                try:
                    for module,before,*_ in self._reversed(self._modules):
                        self._vars(module)['pin']=before['pin'];self._vars(module)['load']=before['load']
                finally:self._modules.clear();self.memo.close();self._active=False
        if cleanup is not None:
            if primary is not None:
                cause=primary.__cause__
                raise primary from (cleanup if cause is None else self._group('pin memo cleanup failed',(cause,cleanup)))
            raise cleanup
        return False
