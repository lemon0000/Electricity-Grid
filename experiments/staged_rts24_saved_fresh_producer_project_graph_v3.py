"""Bounded project-object continuity graphs; observations grant no authority."""
import ast
import abc
import _abc
import builtins
import ctypes
import dataclasses
import dis
import enum
import functools
from fractions import Fraction
import __future__
import gc
from hashlib import sha256
from importlib.machinery import (ModuleSpec,SourceFileLoader,SourcelessFileLoader,
    ExtensionFileLoader,BuiltinImporter,FrozenImporter)
import json
import math
import os
import re
from pathlib import Path
import sys
import typing
import types
import weakref
from threading import get_ident
from types import (ModuleType,FunctionType,CodeType,CellType,MappingProxyType,
    GetSetDescriptorType,MemberDescriptorType,BuiltinFunctionType,WrapperDescriptorType,
    MethodDescriptorType,MethodWrapperType,GenericAlias,UnionType,SimpleNamespace)

PATH_TYPE=type(Path())
EXTERNAL_CALLABLES=(BuiltinFunctionType,WrapperDescriptorType,MethodDescriptorType,MethodWrapperType)
SENTINEL_NAMES=('MISSING','KW_ONLY','_HAS_DEFAULT_FACTORY','_FIELD','_FIELD_CLASSVAR','_FIELD_INITVAR')
SENTINELS=tuple(getattr(dataclasses,name) for name in SENTINEL_NAMES)
DEFAULT_CAPS=(37,50000,256,8388608)
MAX_SOURCE_BYTES=2097152
SAFE_LOADERS=(SourceFileLoader,SourcelessFileLoader,ExtensionFileLoader)
NOT_IMPLEMENTED=NotImplemented
CLASS_METAS=(type,abc.ABCMeta,type(typing.Protocol),enum.EnumType,
    type(ctypes.Structure),type(ctypes.Union),type(ctypes.Array),type(ctypes.c_int),
    type(ctypes.POINTER(ctypes.c_int)),type(ctypes._CFuncPtr),type(typing.Any))
CTYPE_STRUCT_METAS=(type(ctypes.Structure),type(ctypes.Union))
TYPING_FORMS=(typing.Literal,typing.Union,typing.Optional,typing.ClassVar,typing.Final,
    typing.NoReturn,typing.Never,typing.TypeAlias,typing.Unpack,typing.Concatenate)
TYPING_ALIAS_TYPES=tuple(set(type(value) for value in (typing.List,typing.List[int],typing.Optional[int],
    typing.Callable[[int],str],typing.Literal['x'],typing.Tuple[int,...],typing.Annotated[int,'x'])))
PATTERN_TYPE=type(re.compile(''))
FUTURE_FEATURE_TYPE=type(__future__.annotations)
RUNTIME_SEQUENCE_TYPES=(type(sys.version_info),type(sys.flags),type(sys.float_info),type(sys.int_info),type(sys.hash_info))
LRU_WRAPPER_TYPE=type(functools.lru_cache()(lambda:None))


def _cfield_type():
    class Probe(ctypes.Structure):_fields_=[('value',ctypes.c_int)]
    return type(vars(Probe)['value'])


CFIELD_TYPE=_cfield_type()
FALSE_FIELDS=('initial_project_state_authenticated','independent_tcb_authenticated','full_runtime_binding_verified',
    'producer_capability_verified','full_P1_content_verified','role_bootstrap','permit_issued',
    'run_authority','resource_admission','scientific_evidence_adopted','formal_result','actual_F')


def require(value,message):
    if not value:raise ValueError(message)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return (len(raw),sha256(raw).hexdigest())


def _namespace(module):
    require(type(module) is ModuleType,'exact module required')
    value=vars(module);require(all(type(key) is str for key in value),'module namespace string keys required')
    return value


def _path_raw(value):
    require(type(value) is PATH_TYPE,'exact Path required')
    raw=object.__getattribute__(value,'_raw_paths')
    require(type(raw) is list and all(type(item) is str for item in raw),'ordinary Path parts required')
    for name,typ in (('_drv',str),('_root',str),('_tail_cached',list),('_str',str),('_str_normcase_cached',str),
            ('_parts_normcase_cached',list),('_lines_cached',str),('_hash',int)):
        try:item=object.__getattribute__(value,name)
        except AttributeError:continue
        require(type(item) is typ and (typ is not list or all(type(part) is str for part in item)),'unsupported Path cache state')
    return raw


def module_metadata(module):
    namespace=_namespace(module);spec=namespace.get('__spec__');loader=namespace.get('__loader__')
    require(type(spec) is ModuleSpec or spec is None,'ordinary module spec required')
    require(loader is None or loader is BuiltinImporter or loader is FrozenImporter or type(loader) in SAFE_LOADERS,'unsupported module loader')
    attrs={} if spec is None else vars(spec)
    require(all(type(key) is str for key in attrs),'module spec string keys required')
    locations=attrs.get('submodule_search_locations')
    require(locations is None or type(locations) in (list,tuple) and all(type(item) is str for item in locations),'ordinary module search locations required')
    spec_data=None if spec is None else (attrs.get('name'),attrs.get('origin'),None if locations is None else tuple(locations))
    loader_vars={} if loader is None else vars(loader)
    require(all(type(key) is str for key in loader_vars),'module loader string keys required')
    loader_data=None if loader is None else (type(loader).__module__,type(loader).__qualname__,loader_vars.get('name'),loader_vars.get('path'))
    fields=(namespace.get('__name__'),namespace.get('__file__'),namespace.get('__package__'),namespace.get('__version__'),spec_data,loader_data)
    require(all(value is None or type(value) is str for value in fields[:4]),'ordinary module metadata strings required')
    if spec_data is not None:require(all(value is None or type(value) is str for value in spec_data[:2]),'ordinary spec name/origin required')
    if loader_data is not None:require(all(value is None or type(value) is str for value in loader_data),'ordinary loader metadata required')
    return fields,(spec,loader,attrs.get('loader'),locations)


def _under(path,root):
    return type(path) is str and Path(path).is_absolute() and Path(path).is_relative_to(root)


def _registry_image(registry,selected,root):
    rows=[]
    for name,module in tuple(registry.items()):
        require(type(name) is str,'registry string keys required')
        if type(module) is not ModuleType:continue
        path=_namespace(module).get('__file__')
        if name in selected or _under(path,root):
            require(name in selected,'unselected project module or alias: '+name)
            require(module is selected[name],'project registry identity differs: '+name)
            rows.append((name,module))
    require(set(name for name,_ in rows)==set(selected),'missing project registry member')
    return tuple(sorted(rows))


def _build(modules,sources,root,registry,caps):
    _path_raw(root);require(root.is_absolute(),'absolute project root required')
    require(type(modules) is dict and modules and type(sources) is dict
        and all(type(key) is str for key in modules) and all(type(key) is str for key in sources)
        and set(modules)==set(sources),'closed project module/source mapping required')
    require(type(registry) is dict and type(caps) is tuple and len(caps)==4
        and all(type(value) is int and 0<value<=bound for value,bound in zip(caps,DEFAULT_CAPS)),'fixed bounded graph caps required')
    max_modules,max_nodes,max_depth,max_bytes=caps
    require(len(modules)<=max_modules,'project module cap')
    require(all(type(item) is tuple and len(item)==2 and type(item[0]) is str and type(item[1]) is bytes for item in sources.values()),'immutable source bytes required')
    require(sum(len(item[1]) for item in sources.values())<=min(MAX_SOURCE_BYTES,max_bytes),'project source byte cap')
    require(len({str(root/relative).casefold() for relative,_ in sources.values()})==len(sources),'project source path alias')
    declared_classes={}
    for name,module in modules.items():
        require(type(module) is ModuleType and _namespace(module).get('__name__')==name,'exact named project module required')
        require(type(sources[name]) is tuple and len(sources[name])==2,'immutable source pair required')
        relative,raw=sources[name]
        require(type(relative) is str and type(raw) is bytes and not Path(relative).is_absolute()
            and '..' not in Path(relative).parts,'relative source bytes required')
        require(_namespace(module).get('__file__')==str(root/relative),'project source origin differs')
        for item in ast.parse(raw).body:
            if type(item) is ast.ClassDef:
                cls=vars(module).get(item.name)
                require(type(cls) in CLASS_METAS and cls.__module__==name and cls.__name__==cls.__qualname__==item.name,
                    'source-declared project class owner differs')
                declared_classes[id(cls)]=name
    before=_registry_image(registry,modules,root)
    namespaces={id(vars(module)):name for name,module in modules.items()}
    seen={};objects=[];nodes=[];conditional=[];fallbacks=[];attributes=[];global_refs=[];metadata_namespaces=set();charged=0
    abc_owners={id(vars(value)['_abc_impl']):value for module in modules.values() for value in vars(module).values()
        if type(value) in (abc.ABCMeta,type(typing.Protocol)) and '_abc_impl' in vars(value)}
    cfield_owners={id(item):(value,name) for module in modules.values() for value in vars(module).values()
        if type(value) in CTYPE_STRUCT_METAS for name,item in vars(value).items() if type(item) is CFIELD_TYPE}
    def account(value):
        nonlocal charged
        charged+=len(canonical(value));require(charged<=max_bytes,'project graph byte cap')
        return value
    def atom(value):
        typ=type(value)
        if value is None or typ in (str,bool,int):return (typ.__name__,value)
        if typ is float:require(math.isfinite(value),'nonfinite graph atom');return ('float',value)
        if typ is complex:
            require(math.isfinite(value.real) and math.isfinite(value.imag),'nonfinite graph atom')
            return ('complex',value.real,value.imag)
        raise ValueError('unsupported graph mapping/set key')
    def ordered(mapping):
        if type(mapping) is MappingProxyType:
            refs=gc.get_referents(mapping)
            require(len(refs)==1 and type(refs[0]) is dict,'mapping proxy must wrap an exact dictionary')
            mapping=refs[0]
        require(type(mapping) is dict,'exact graph dictionary required')
        return sorted(mapping.items(),key=lambda item:sort_key(item[0]))
    def sort_key(value):
        typ=type(value)
        if value is None or typ in (str,bool,int,float,complex):return b'a'+canonical(atom(value))
        if typ in CLASS_METAS or type(typ) is enum.EnumType or typ in (bytes,Fraction,PATH_TYPE):return b'b'+canonical((id(typ),id(value)))
        if typ is tuple:return b'c'+canonical(tuple(sort_key(item).hex() for item in value))
        if typ is frozenset:return b'd'+canonical(sorted(sort_key(item).hex() for item in value))
        raise ValueError('unsupported graph mapping/set key')
    def external(module,depth):
        require(type(module) is ModuleType,'conditional external module required')
        metadata,refs=module_metadata(module);name=metadata[0]
        if refs[0] is not None and type(vars(refs[0]).get('loader_state')) is SimpleNamespace:
            metadata_namespaces.add(id(vars(refs[0])['loader_state']))
        require(type(name) is str and registry.get(name) is module and not _under(metadata[1],root),'unowned project external module')
        index=len(conditional);conditional.append((module,metadata,refs))
        return ('conditional_module',index,metadata,visit(refs[0],depth+1),visit(refs[1],depth+1))
    def visit(value,depth=0):
        require(depth<=max_depth,'project graph depth cap')
        typ=type(value)
        if value is None or typ in (str,bool,int,float,complex):
            if typ is str:require(len(value)<=max_bytes,'project graph byte cap')
            return account(atom(value))
        identity=id(value)
        if identity in seen:return ('ref',seen[identity])
        require(len(nodes)<max_nodes,'project graph node cap')
        index=len(nodes);seen[identity]=index;objects.append(value);nodes.append(None)
        def edge(item):return visit(item,depth+1)
        def mapping(items):return tuple((edge(key),edge(item)) for key,item in ordered(items))
        if typ is ModuleType:
            name=_namespace(value).get('__name__')
            if name in modules:
                require(value is modules[name],'project module alias differs')
                metadata,refs=module_metadata(value);conditional.append((value,metadata,refs))
                if refs[0] is not None and type(vars(refs[0]).get('loader_state')) is SimpleNamespace:
                    metadata_namespaces.add(id(vars(refs[0])['loader_state']))
                omitted={'__name__','__file__','__package__','__version__'}
                row=('project_module',name,metadata,mapping({key:item for key,item in _namespace(value).items() if key not in omitted}))
            else:row=external(value,depth)
        elif typ is FunctionType:
            context=value.__globals__;require(all(type(key) is str for key in context),'function namespace string keys required')
            owner=namespaces.get(id(context))
            if owner is None:
                require(not _under(context.get('__file__'),root) and not _under(value.__code__.co_filename,root),'foreign project function globals')
                owners={id(module):module for module in registry.values() if type(module) is ModuleType and vars(module) is context}
                require(len(owners)==1,'unowned conditional function globals');module=next(iter(owners.values()))
                row=('conditional_function',edge(module),value.__name__,value.__qualname__,edge(value.__code__),
                    edge(value.__defaults__),edge(value.__kwdefaults__),edge(value.__closure__),edge(value.__annotations__),edge(vars(value)))
            else:
                require(value.__module__==owner,'project function declared owner differs')
                require(context is vars(modules[owner]),'project function globals differ')
                builtins_value=context.get('__builtins__')
                lookup=vars(builtins_value) if type(builtins_value) is ModuleType else builtins_value
                require(type(lookup) is dict and value.__builtins__ is lookup,'original project function builtins dictionary required')
                row=('project_function',edge(modules[owner]),value.__name__,value.__qualname__,edge(value.__code__),
                    edge(value.__defaults__),edge(value.__kwdefaults__),edge(value.__closure__),edge(value.__annotations__),edge(vars(value)),edge(lookup))
                names=set()
                def loads(code):
                    names.update(item.argval for item in dis.get_instructions(code) if item.opname in ('LOAD_GLOBAL','LOAD_NAME'))
                    for item in code.co_consts:
                        if type(item) is CodeType:loads(item)
                loads(value.__code__)
                for name in sorted(names):
                    if name not in context:
                        require(name in lookup,'unbound project global: '+name)
                        fallbacks.append(account((owner,name,edge(lookup[name]))))
                def static_edges(code):
                    current=None
                    for instruction in dis.get_instructions(code):
                        if instruction.opname in ('LOAD_GLOBAL','LOAD_NAME'):
                            name=instruction.argval;is_global=name in context;target=context[name] if is_global else lookup[name]
                            global_refs.append(account((owner,value.__qualname__,name,'global' if is_global else 'builtin',edge(target))))
                            current=(name,(),target)
                        elif instruction.opname in ('LOAD_ATTR','LOAD_METHOD') and current is not None:
                            name,path,target=current;attribute=instruction.argval
                            if type(target) is ModuleType:tables=(_namespace(target),)
                            elif type(target) in CLASS_METAS:tables=tuple(vars(base) for base in target.__mro__)
                            else:current=None;continue
                            require(all(all(type(key) is str for key in table) for table in tables),'static attribute table string keys required')
                            matches=[table[attribute] for table in tables if attribute in table]
                            require(matches,'dynamic module/class attribute is unsupported')
                            target=matches[0];path=path+(attribute,)
                            attributes.append(account((owner,value.__qualname__,name,path,edge(target))))
                            current=(name,path,target)
                        else:current=None
                    for item in code.co_consts:
                        if type(item) is CodeType:static_edges(item)
                static_edges(value.__code__)
        elif typ is CodeType:
            require(2*(len(value.co_code)+len(value.co_linetable)+len(value.co_exceptiontable))<=max_bytes,'project graph byte cap')
            attrs=tuple((name,getattr(value,name)) for name in ('co_argcount','co_posonlyargcount','co_kwonlyargcount','co_nlocals','co_stacksize','co_flags',
                'co_names','co_varnames','co_filename','co_name','co_qualname','co_firstlineno','co_freevars','co_cellvars'))
            row=('code',attrs,value.co_code.hex(),value.co_linetable.hex(),value.co_exceptiontable.hex(),tuple(edge(item) for item in value.co_consts))
        elif typ is CellType:
            try:content=value.cell_contents
            except ValueError:row=('empty_cell',)
            else:row=('cell',edge(content))
        elif typ in CLASS_METAS:
            name=value.__module__
            if identity in declared_classes:require(name==declared_classes[identity],'source class module changed')
            if name in modules:
                require(typ in CLASS_METAS,'project custom metaclass is unsupported')
                attrs=vars(value)
                if typ in CTYPE_STRUCT_METAS:
                    fields=attrs.get('_fields_',())
                    require(type(fields) in (list,tuple) and all(type(item) is tuple and len(item) in (2,3)
                        and type(item[0]) is str and type(item[1]) in CLASS_METAS
                        and (len(item)==2 or type(item[2]) is int) for item in fields),'ordinary ctypes source fields required')
                    descriptors=tuple((item[0],attrs[item[0]]) for item in fields)
                    require(all(type(descriptor) is CFIELD_TYPE for _,descriptor in descriptors),'exact ctypes field descriptors required')
                    layout=tuple((name,descriptor.offset,descriptor.size) for name,descriptor in descriptors)
                    row=('project_ctypes_class',edge(modules[name]),value.__name__,value.__qualname__,edge(value.__bases__),
                        edge(value.__mro__),mapping({key:item for key,item in attrs.items() if key not in dict(descriptors)}),
                        ctypes.sizeof(value),ctypes.alignment(value),layout)
                else:
                    row=('project_class',edge(modules[name]),value.__name__,value.__qualname__,edge(value.__bases__),
                        edge(value.__mro__),mapping(attrs))
            else:
                module=registry.get(name)
                if type(module) is ModuleType and vars(module).get(value.__name__) is value:
                    row=('conditional_class',edge(module),value.__name__,value.__qualname__)
                elif value is ctypes.Structure.__base__:
                    ctypes_module=registry.get('ctypes')
                    require(type(ctypes_module) is ModuleType and vars(ctypes_module).get('Structure') is ctypes.Structure,
                        'conditional ctypes base owner changed')
                    row=('conditional_ctypes_base',edge(ctypes_module),value.__name__,value.__qualname__)
                else:
                    type_module=registry.get('types');require(type(type_module) is ModuleType,'conditional types module required')
                    aliases=[key for key,item in vars(type_module).items() if item is value]
                    require(aliases,'unowned conditional class')
                    row=('conditional_type_alias',edge(type_module),tuple(sorted(aliases)),value.__name__,value.__qualname__)
        elif typ is ModuleSpec:
            state=vars(value)
            if type(state.get('loader_state')) is SimpleNamespace:metadata_namespaces.add(id(state['loader_state']))
            row=('module_spec_state',mapping(state))
        elif typ is SimpleNamespace and identity in metadata_namespaces:row=('module_spec_namespace',mapping(vars(value)))
        elif typ in SAFE_LOADERS:row=('module_loader_state',typ.__module__,typ.__qualname__,mapping(vars(value)))
        elif typ in (dict,MappingProxyType):row=(typ.__name__,mapping(value))
        elif typ in (tuple,list):row=(typ.__name__,tuple(edge(item) for item in value))
        elif typ in (set,frozenset):row=(typ.__name__,tuple(edge(item) for item in sorted(value,key=sort_key)))
        elif typ is bytes:row=('bytes',pin(value))
        elif value is Ellipsis:row=('ellipsis',)
        elif value is NOT_IMPLEMENTED:
            require(_namespace(builtins).get('NotImplemented') is value,'NotImplemented builtin owner changed')
            row=('not_implemented',)
        elif any(value is item for item in SENTINELS):
            i=next(i for i,item in enumerate(SENTINELS) if value is item)
            require(_namespace(dataclasses).get(SENTINEL_NAMES[i]) is value,'dataclass sentinel owner changed')
            row=('dataclass_sentinel',i)
        elif typ is PATH_TYPE:
            raw_paths=_path_raw(value)
            expected=PATH_TYPE(*raw_paths)
            require(str(value)==str(expected) and value.parts==expected.parts and value==expected and hash(value)==hash(expected),'Path derived state differs')
            row=('path',str(expected),tuple(raw_paths))
        elif typ in (staticmethod,classmethod):row=(typ.__name__,edge(value.__func__),edge(vars(value)))
        elif typ is property:row=('property',edge(value.fget),edge(value.fset),edge(value.fdel),edge(value.__doc__))
        elif typ in (GetSetDescriptorType,MemberDescriptorType):row=(typ.__name__,value.__name__,edge(value.__objclass__),edge(value.__doc__))
        elif typ in (dataclasses.Field,dataclasses._DataclassParams,dataclasses.InitVar):
            slots=typ.__slots__;slots=(slots,) if type(slots) is str else slots
            row=('dataclass_metadata',typ.__name__,tuple((name,edge(object.__getattribute__(value,name))) for name in slots))
        elif typ is GenericAlias:row=('generic_alias',edge(value.__origin__),edge(value.__args__))
        elif typ is UnionType:row=('union_type',edge(value.__args__))
        elif typ is Fraction:
            numerator=object.__getattribute__(value,'_numerator');denominator=object.__getattribute__(value,'_denominator')
            require(type(numerator) is type(denominator) is int and denominator>0
                and math.gcd(numerator,denominator)==1,'canonical Fraction fields required')
            row=('fraction',numerator,denominator)
        elif typ is PATTERN_TYPE:
            require(type(value.pattern) in (str,bytes),'ordinary regex pattern required')
            row=('regex_pattern',edge(value.pattern),value.flags,value.groups,mapping(dict(value.groupindex)))
        elif any(value is form for form in TYPING_FORMS):
            i=next(index for index,form in enumerate(TYPING_FORMS) if value is form)
            name=object.__getattribute__(value,'_name');function=object.__getattribute__(value,'_getitem')
            require(vars(typing).get(name) is value and type(function) is FunctionType
                and function.__globals__ is vars(typing),'original conditional typing form required')
            row=('conditional_typing_form',i,name,edge(object.__getattribute__(value,'__doc__')),
                edge(function))
        elif typ in TYPING_ALIAS_TYPES:
            row=('typing_alias',id(typ),edge(typing.get_origin(value)),edge(typing.get_args(value)),mapping(vars(value)))
        elif typ is FUTURE_FEATURE_TYPE:
            state=vars(value);require(set(state)=={'optional','mandatory','compiler_flag'},'exact future feature fields required')
            row=('future_feature',mapping(state))
        elif type(typ) is enum.EnumType:
            row=('enum_member',edge(typ),mapping(vars(value)))
        elif identity in abc_owners:
            cls=abc_owners[identity];registry_set,cache,negative,version=_abc._get_dump(cls)
            def weak_targets(items):
                require(all(type(item) is weakref.ReferenceType for item in items),'ordinary ABC cache weakrefs required')
                return tuple(edge(weakref.ReferenceType.__call__(item)) for item in sorted(items,key=lambda item:id(weakref.ReferenceType.__call__(item))))
            row=('abc_cache',edge(cls),weak_targets(registry_set),weak_targets(cache),weak_targets(negative),version)
        elif typ is CFIELD_TYPE:
            require(identity in cfield_owners,'unowned ctypes field descriptor')
            cls,name=cfield_owners[identity];row=('ctypes_field',edge(cls),name,value.offset,value.size)
        elif typ in RUNTIME_SEQUENCE_TYPES:
            row=('runtime_struct_sequence',id(typ),tuple(edge(item) for item in tuple.__iter__(value)))
        elif typ is os._Environ:
            state=vars(value);require(set(state)=={'encodekey','decodekey','encodevalue','decodevalue','_data'},'exact environment mapping fields required')
            row=('conditional_environment',mapping(state))
        elif typ is LRU_WRAPPER_TYPE:
            require(type(vars(value).get('__wrapped__')) is FunctionType,'original conditional cache wrapper required')
            row=('conditional_lru_wrapper',mapping(vars(value)))
        elif typ in EXTERNAL_CALLABLES:
            name=getattr(value,'__module__',None);owner=getattr(value,'__objclass__',None)
            if owner is not None:row=('conditional_descriptor',edge(owner),value.__name__)
            else:
                bound=getattr(value,'__self__',None)
                if type(bound) in CLASS_METAS:
                    members=[vars(base).get(value.__name__) for base in bound.__mro__]
                    members=[item.__func__ if type(item) in (staticmethod,classmethod) else item for item in members]
                    require(any(item is value for item in members),'unowned conditional bound builtin')
                    row=('conditional_bound_builtin',edge(bound),value.__name__)
                else:
                    module=registry.get(name);require(type(module) is ModuleType and vars(module).get(value.__name__) is value,'unowned conditional builtin')
                    row=('conditional_builtin',edge(module),value.__name__,getattr(value,'__qualname__',value.__name__))
        else:raise ValueError('unsupported project graph value')
        nodes[index]=account(row);return ('ref',index)
    roots=tuple((name,visit(modules[name])) for name in sorted(modules))
    root_ref=visit(root)
    after=_registry_image(registry,modules,root)
    require(before==after,'project registry changed during snapshot')
    source_pins=tuple((name,sources[name][0],pin(sources[name][1])) for name in sorted(sources))
    graph=(roots,tuple(nodes),source_pins,tuple(sorted(set(fallbacks))),tuple(sorted(set(attributes))),tuple(sorted(set(global_refs))),root_ref)
    raw=canonical(graph);require(len(raw)<=max_bytes,'project graph byte cap')
    return graph,tuple(objects),tuple(conditional)


class ProducerProjectSnapshot:
    __slots__=('_modules','_sources','_root','_registry','_caps','_graph','_objects','_conditional','_creator','_seal')
    def __new__(cls,*args,**kwargs):raise TypeError('capture an observation explicitly')
    def __setattr__(self,name,value):raise AttributeError('snapshot fields are frozen')
    def __delattr__(self,name):raise AttributeError('snapshot fields are frozen')
    def __reduce__(self):raise TypeError('project object identities are process-local')
    def __copy__(self):raise TypeError('project snapshots cannot be copied')
    def __deepcopy__(self,memo):raise TypeError('project snapshots cannot be copied')


def _image(snapshot):
    return (pin(canonical(snapshot._graph)),tuple(map(id,snapshot._objects)),snapshot._creator,snapshot._caps,
        tuple((name,id(module)) for name,module in snapshot._modules),
        tuple((name,relative,pin(raw),id(raw)) for name,(relative,raw) in snapshot._sources),str(snapshot._root),id(snapshot._registry),
        tuple((id(module),metadata,tuple(map(id,refs))) for module,metadata,refs in snapshot._conditional))

def capture(modules,sources,root,*,registry=None,caps=DEFAULT_CAPS):
    """Observe a closed project set without importing, executing, or reading sources."""
    if registry is None:registry=sys.modules
    require(type(modules) is dict and type(sources) is dict,'closed input maps required')
    modules=dict(modules);sources=dict(sources)
    graph,objects,conditional=_build(modules,sources,root,registry,caps)
    snapshot=object.__new__(ProducerProjectSnapshot)
    for name,value in dict(_modules=tuple(sorted(modules.items())),_sources=tuple(sorted(sources.items())),_root=root,
            _registry=registry,_caps=caps,_graph=graph,_objects=objects,_conditional=conditional,_creator=(os.getpid(),get_ident())).items():
        object.__setattr__(snapshot,name,value)
    object.__setattr__(snapshot,'_seal',pin(canonical(_image(snapshot))))
    return snapshot


def check(snapshot):
    require(type(snapshot) is ProducerProjectSnapshot and snapshot._creator==(os.getpid(),get_ident()),'creating project snapshot required')
    require(snapshot._seal==pin(canonical(_image(snapshot))),'snapshot identity seal changed')
    graph,objects,conditional=_build(dict(snapshot._modules),dict(snapshot._sources),snapshot._root,snapshot._registry,snapshot._caps)
    require(graph==snapshot._graph and len(objects)==len(snapshot._objects)
        and all(a is b for a,b in zip(objects,snapshot._objects)),'project structure or identity changed')
    require(len(conditional)==len(snapshot._conditional) and all(a[0] is b[0] and a[1]==b[1]
        and all(x is y for x,y in zip(a[2],b[2])) for a,b in zip(conditional,snapshot._conditional)),
        'conditional TCB metadata changed')
    return dict(schema='staged_saved_F_project_continuity_observation_v1',authority='DRAFT_NONAUTHORITATIVE',
        modules=len(snapshot._modules),nodes=len(objects),graph_pin=pin(canonical(graph)),structure_and_identity_stable=True,
        **{name:False for name in FALSE_FIELDS})


def current():
    """Fixed source/contract metadata only; no project graph or P1 operation."""
    root=Path(__file__).absolute().parents[1]
    ledger=root/'results/tables/staged_rts24_saved_fresh_full_producer_bridge_v3_non_authoritative'
    raw=(ledger/'checkpoint.json').read_bytes()
    require(pin(raw)[1]=='71b32f62900411f30a985c7cb15b07733863037d6f3bbd0b39cd65d823e6f998','fixed code bridge checkpoint required')
    cp=json.loads(raw);require(cp['accepted'] is cp['diagnostic_accepted'] is cp['accounting_complete'] is True,'accepted code bridge required')
    reg_raw=(ledger/'registration.json').read_bytes();require(pin(reg_raw)==(cp['known_pins'][str(ledger/'registration.json')]['bytes'],cp['known_pins'][str(ledger/'registration.json')]['sha256']),'bridge registration differs')
    reg=json.loads(reg_raw);source=reg['derivation']['source_contract']
    require(len(source['source_pins'])==49 and source['source_epoch']==pin(canonical(source['source_pins']))[1]
        =='acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875','fixed Source49 required')
    for path,expected in source['source_pins'].items():
        value=pin((root/path).read_bytes());require(value==(expected['bytes'],expected['sha256']),'source differs: '+path)
    unit=compile(Path(__file__).read_bytes(),str(Path(__file__).absolute()),'exec',dont_inherit=True,optimize=0)
    roots=[item.co_name for item in unit.co_consts if type(item) is CodeType]
    return None,dict(schema='staged_saved_F_producer_project_graph_contract_v3',authority='DRAFT_NONAUTHORITATIVE',
        source_contract=source,bridge_checkpoint_pin=pin(raw),roots=roots,default_caps=DEFAULT_CAPS,
        source_byte_cap=MAX_SOURCE_BYTES,
        operation='project_object_continuity_observation_only',source49_target_modules_executed=0,P1_reads=0,
        explicit_type_rows=('Fraction','Pattern','typing_forms_and_aliases','ProtocolMeta','ctypes_structure','Enum','future_feature','ABC_cache'),
        **{name:False for name in FALSE_FIELDS})
