"""Bounded callable observations that never invoke object representations."""
from types import FunctionType,ModuleType
from weakref import ref


def literal(value):
    remaining=[8192];active=set()
    def visit(item,depth):
        remaining[0]-=1
        if depth>32 or remaining[0]<0:raise ValueError('bounded literal callable declaration required')
        kind=type(item)
        if kind in (type(None),bool,int):return (kind.__name__,item)
        if kind is float:return ('float',float.hex(item))
        if kind in (str,bytes):
            if len(item)>65536:raise ValueError('bounded literal callable scalar required')
            return (kind.__name__,item)
        if kind not in (tuple,list,dict,set,frozenset):
            raise ValueError('exact builtin literal callable declaration required')
        if id(item) in active:raise ValueError('acyclic callable declaration required')
        active.add(id(item))
        try:
            if kind is dict:
                payload=frozenset((visit(key,depth+1),visit(part,depth+1)) for key,part in item.items())
            else:
                payload=tuple(visit(part,depth+1) for part in item)
                if kind in (set,frozenset):payload=frozenset(payload)
            return (kind.__name__,payload)
        finally:active.remove(id(item))
    return visit(value,0)


def signature(function):
    if type(function) is not FunctionType:raise ValueError('exact callable required')
    return (id(function.__code__),id(function.__globals__),id(function.__defaults__),literal(function.__defaults__),
        id(function.__kwdefaults__),literal(function.__kwdefaults__),
        tuple((id(cell),id(cell.cell_contents)) for cell in function.__closure__ or ()),
        id(getattr(function,'__wrapped__',None)))


def weak_observation(function):
    """Keep no function, module, namespace, closure cell or default object alive.

    Private mutable state containers retain their identity. Their contents are
    authenticated by the original source checker. Unobserved identity ABA for
    values that cannot be weak-referenced is outside this observation contract.
    """
    before=signature(function);contents=[]
    for cell in function.__closure__ or ():
        value=cell.cell_contents
        try:reference=ref(value)
        except TypeError:reference=None
        contents.append((reference,id(value)))
    return ref(function),before,tuple(contents)


def check_weak(observation,function):
    reference,before,contents=observation
    if reference() is not function or signature(function)!=before:
        raise ValueError('original callable code/default/global/closure changed')
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
