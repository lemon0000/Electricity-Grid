"""Bounded callable observations that never invoke object representations."""
from hashlib import sha256
from struct import pack
from types import FunctionType
from weakref import ref


def literal(value):
    remaining=[8192,1024*1024];active=set()
    def scalar(kind,item,raw):
        remaining[1]-=len(raw)
        if remaining[1]<0:raise ValueError('bounded aggregate callable scalar bytes required')
        return (kind.__name__,id(item),len(raw),sha256(raw).digest())
    def visit(item,depth):
        remaining[0]-=1
        if depth>32 or remaining[0]<0:raise ValueError('bounded literal callable declaration required')
        kind=type(item)
        if kind is type(None):return ('NoneType',)
        if kind is bool:return ('bool',int(item))
        if kind is int:
            if item.bit_length()>4096:raise ValueError('bounded callable integer required')
            return scalar(kind,item,item.to_bytes((item.bit_length()+8)//8,'big',signed=True))
        if kind is float:return scalar(kind,item,pack('!d',item))
        if kind in (str,bytes):
            if len(item)>65536:raise ValueError('bounded literal callable scalar required')
            return scalar(kind,item,item.encode('utf-8','surrogatepass') if kind is str else item)
        if kind not in (tuple,list,dict,set,frozenset):
            raise ValueError('exact builtin literal callable declaration required')
        if id(item) in active:raise ValueError('acyclic callable declaration required')
        active.add(id(item))
        try:
            if kind is dict:
                payload=tuple((visit(key,depth+1),visit(part,depth+1)) for key,part in item.items())
            else:
                payload=tuple(visit(part,depth+1) for part in item)
            return (kind.__name__,id(item),payload)
        finally:active.remove(id(item))
    return visit(value,0)


def signature(function):
    if type(function) is not FunctionType:raise ValueError('exact callable required')
    return (id(function.__code__),id(function.__globals__),id(function.__defaults__),literal(function.__defaults__),
        id(function.__kwdefaults__),literal(function.__kwdefaults__),
        tuple((id(cell),id(cell.cell_contents)) for cell in function.__closure__ or ()),
        id(getattr(function,'__wrapped__',None)))


def weak_observation(function):
    """Keep no original function, namespace, closure cell or default leaf alive.

    Private mutable state containers retain their identity. Their contents are
    authenticated by the original source checker. Defaults preserve observed
    order, identity and aliases with bounded scalar digests, not owned leaves.
    Code, wrapped objects and closure contents use weakrefs when possible.
    Unobserved ABA for non-weakrefable default containers/leaves, cells and
    wrapped/closure values remains outside this observation contract.
    """
    before=signature(function);contents=[]
    for cell in function.__closure__ or ():
        value=cell.cell_contents
        try:reference=ref(value)
        except TypeError:reference=None
        contents.append((reference,id(value)))
    wrapped=getattr(function,'__wrapped__',None)
    try:wrapped_reference=ref(wrapped)
    except TypeError:wrapped_reference=None
    return ref(function),before,tuple(contents),ref(function.__code__),wrapped_reference


def check_weak(observation,function):
    reference,before,contents,code_reference,wrapped_reference=observation
    if reference() is not function or signature(function)!=before:
        raise ValueError('original callable code/default/global/closure changed')
    if (code_reference() is not function.__code__ or wrapped_reference is not None
            and wrapped_reference() is not getattr(function,'__wrapped__',None)):
        raise ValueError('original callable code/wrapped alias changed')
    for cell,(observed,identity) in zip(function.__closure__ or (),contents):
        value=cell.cell_contents
        if id(value)!=identity or observed is not None and observed() is not value:
            raise ValueError('original callable closure alias changed')


def describe(error):
    try:
        args=vars(BaseException)['args'].__get__(error)
        if type(args) is tuple and args and type(args[0]) is str:return 'BaseException: '+args[0][:160]
    except BaseException:pass
    return 'BaseException'


def note(error,message):
    try:
        if type(message) is not str:return
        namespace=vars(BaseException)['__dict__'].__get__(error)
        notes=namespace.get('__notes__')
        if notes is None:namespace['__notes__']=[message[:240]]
        elif type(notes) is list and len(notes)<16:notes.append(message[:240])
    except BaseException:pass
