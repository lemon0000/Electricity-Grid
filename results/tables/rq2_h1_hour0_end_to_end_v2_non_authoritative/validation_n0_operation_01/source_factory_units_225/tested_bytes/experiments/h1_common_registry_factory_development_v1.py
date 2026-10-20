"""Weak provenance for original source factories; no numerical authority.

The trusted caller supplies literal pins and ordered component/factory names.
Only a compiled module's fixed definition/footer CALLsites may enter. Factories
are constructed from the pinned blueprint, rather than a supplied callable.
Completed observations contain no strong reference to the unloadable graph.
"""
import ast
import builtins
import dataclasses
import dis
from hashlib import sha256
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import sys
from threading import Lock,get_ident
from types import CodeType,FunctionType,ModuleType,MappingProxyType,GetSetDescriptorType,MemberDescriptorType
from weakref import ref

from experiments import h1_validation_callable_state_development_v1 as state


_DEFINE='_define_common_registry_component'
_REGISTER='_register_common_registry_component'
_KINDS=(FunctionType,ModuleType,type,property,staticmethod,classmethod)


def build_factory_provenance(root,pins,families):
    """Return define/register/checked for at most two ordered draft families.

    families maps a name to tuples of (module_name, tuple(factory_names)). Source
    must assign every returned export through the literal definition entry.
    Factories return functions or None. At the first factory, class declarations
    are reconstructed from pinned source in the canonical namespace, after the
    entry checks. Caller-provided class identities never enter a minted factory.
    register is a distinct footer; checked returns diagnostic scalar data only.
    """
    if type(root) not in (str,type(Path())) or type(pins) is not dict or type(families) is not dict:
        raise ValueError('exact builtin factory manifest required')
    if not 1<=len(pins)<=4096 or not 1<=len(families)<=2:
        raise ValueError('bounded factory manifest required')
    for name,pin in pins.items():
        if (type(name) is not str or not name.startswith('experiments.') or len(name)>200
                or not name[len('experiments.'):].isascii() or not name[len('experiments.'):].isidentifier()
                or type(pin) is not str or len(pin)!=64 or any(c not in '0123456789abcdef' for c in pin)):
            raise ValueError('exact factory module name and SHA256 required')
    slots={};plans={}
    for family,components in families.items():
        if type(family) is not str or not 1<=len(family)<=80 or type(components) is not tuple or not 1<=len(components)<=4:
            raise ValueError('bounded immutable factory family required')
        for index,component in enumerate(components):
            if (type(component) is not tuple or len(component)!=2 or type(component[0]) is not str
                    or component[0] not in pins or component[0] in slots or type(component[1]) is not tuple
                    or not 1<=len(component[1])<=8 or any(type(n) is not str or not n.isascii()
                        or not n.isidentifier() or len(n)>160 for n in component[1])
                    or len(set(component[1]))!=len(component[1])):
                raise ValueError('disjoint ordered factory components required')
            slots[component[0]]=(family,index,component[1])
        plans[family]=tuple(components)
    directory=Path(root).resolve(strict=True);expected=dict(pins);schemas={}
    frame_at=sys._getframe;lock=Lock();creator=(os.getpid(),get_ident())
    progress={family:[0,0,'ready'] for family in plans};observations={};class_states={};used=set()

    def read_source(name):
        path=directory/(name.rsplit('.',1)[-1]+'.py')
        with path.open('rb') as stream:raw=stream.read(2*1024*1024+1)
        if len(raw)>2*1024*1024 or sha256(raw).hexdigest()!=expected[name]:
            raise ValueError('bounded predeclared factory source pin differs')
        return path,raw

    def target_names(node):
        if type(node) is ast.Name:return (node.id,)
        if type(node) in (ast.Tuple,ast.List):return sum((target_names(part) for part in node.elts),())
        raise ValueError('literal factory export assignment required')

    total_source_bytes=0;dependency_sources={}
    for declared in expected:
        source_path,source_raw=read_source(declared)
        dependency_sources[declared]=(compile(source_raw,str(source_path),'exec',dont_inherit=True),ast.parse(source_raw))
        total_source_bytes+=len(source_raw)
        if total_source_bytes>32*1024*1024:raise ValueError('bounded aggregate factory source bytes required')

    def semantics(value):
        """Compare source literals without invoking equality or representations."""
        aliases={}
        def normalize(part):
            kind=part[0]
            if kind in ('NoneType','bool'):return part
            if kind in ('int','float','str','bytes'):return (kind,part[2],part[3])
            identity=part[1]
            if identity in aliases:return ('alias',aliases[identity])
            ordinal=len(aliases);aliases[identity]=ordinal
            payload=tuple((normalize(k),normalize(v)) for k,v in part[2]) if kind=='dict' else tuple(normalize(v) for v in part[2])
            return kind,ordinal,payload
        return normalize(state.literal(value))

    def defaults(function,node):
        try:
            positional=tuple(ast.literal_eval(value) for value in node.args.defaults) or None
            keywords={key.arg:ast.literal_eval(value) for key,value in zip(node.args.kwonlyargs,node.args.kw_defaults)
                if value is not None} or None
        except (ValueError,TypeError):
            raise ValueError('source-specific contract required for nonliteral authored defaults') from None
        if (semantics(function.__defaults__)!=semantics(positional)
                or semantics(function.__kwdefaults__)!=semantics(keywords)
                or getattr(function,'__wrapped__',None) is not None):
            raise ValueError('original source-declared callable defaults required')

    def function_code(code,qualname):
        if code.co_qualname==qualname:return code
        for child in code.co_consts:
            if type(child) is CodeType:
                found=function_code(child,qualname)
                if found is not None:return found
        return None

    def generated_dataclass(node):
        """Independent stdlib templates for the field-only draft classes."""
        decorators=node.decorator_list
        if not decorators:return {}
        if (len(decorators)!=1 or type(decorators[0]) is not ast.Call
                or entry_name(decorators[0].func)!='dataclass' or decorators[0].args):
            raise ValueError('explicit supported source class decorator required')
        options={keyword.arg:ast.literal_eval(keyword.value) for keyword in decorators[0].keywords}
        if (set(options)-{'init','repr','eq','order','unsafe_hash','frozen','match_args','kw_only'}
                or any(type(value) is not bool for value in options.values()) or options.get('init',True)):
            raise ValueError('explicit init-free source dataclass required')
        fields=[];namespace={}
        for child in node.body:
            if type(child) is ast.AnnAssign:
                if type(child.target) is not ast.Name or child.value is not None:
                    raise ValueError('field-only source dataclass declaration required')
                fields.append((child.target.id,object))
            elif type(child) in (ast.FunctionDef,ast.AsyncFunctionDef):
                namespace[child.name]=lambda:None
        template=dataclasses.make_dataclass(node.name,fields,namespace=namespace,**options)
        result={}
        authored={child.name for child in node.body if type(child) in (ast.FunctionDef,ast.AsyncFunctionDef)}
        for key,value in vars(template).items():
            if type(value) is FunctionType and key not in authored:
                if key=='__repr__':
                    cells=dict(zip(value.__code__.co_freevars,(cell.cell_contents for cell in value.__closure__ or ())))
                    result[key]=(value.__code__,cells['user_function'].__code__)
                else:result[key]=(value.__code__,)
        return result

    def entry_name(node):
        return node.id if type(node) is ast.Name else node.attr if type(node) is ast.Attribute else None

    def module_argument(node):
        return (type(node) is ast.Subscript and type(node.value) is ast.Attribute
            and type(node.value.value) is ast.Name and node.value.value.id=='sys'
            and node.value.attr=='modules' and type(node.slice) is ast.Name and node.slice.id=='__name__')

    for name,(family,index,factories) in slots.items():
        path,raw=read_source(name);tree=ast.parse(raw)
        code=compile(raw,str(path),'exec',dont_inherit=True);blueprints={};pending=[code]
        while pending:
            current=pending.pop();blueprints[current.co_qualname]=current
            pending.extend(value for value in current.co_consts if type(value) is CodeType)
        events=[];dynamic=set();class_fields={}
        for node in ast.walk(tree):
            if type(node) is ast.ClassDef:
                class_fields[node.name]={part.name for part in node.body if type(part) in (ast.FunctionDef,ast.AsyncFunctionDef)}
            if (type(node) is ast.Attribute and type(node.ctx) is ast.Store
                    and type(node.value) is ast.Name and node.value.id=='module'):dynamic.add(node.attr)
            if (type(node) is ast.Subscript and type(node.ctx) is ast.Store and type(node.value) is ast.Name
                    and node.value.id in ('namespace','globals') and type(node.slice) is ast.Constant
                    and type(node.slice.value) is str):dynamic.add(node.slice.value)
        instructions=tuple(dis.get_instructions(code,show_caches=True))
        for node in tree.body:
            expression=node.value if type(node) in (ast.Assign,ast.AnnAssign,ast.Expr) else None
            if type(expression) is not ast.Call or entry_name(expression.func) not in (_DEFINE,_REGISTER):continue
            entry=entry_name(expression.func)
            if expression.keywords or not expression.args or not module_argument(expression.args[0]):
                raise ValueError('literal factory source entry required')
            if entry==_DEFINE:
                if (len(expression.args)!=2 or type(expression.args[1]) is not ast.Constant
                        or type(expression.args[1].value) is not str):raise ValueError('literal factory name required')
                factory=expression.args[1].value
                if type(node) is ast.Expr:exports=()
                elif type(node) is ast.Assign and len(node.targets)==1:exports=target_names(node.targets[0])
                elif type(node) is ast.AnnAssign:exports=target_names(node.target)
                else:raise ValueError('one factory export assignment required')
            else:
                if len(expression.args)!=1 or type(node) is not ast.Expr:raise ValueError('literal factory footer required')
                factory=None;exports=()
            position=(expression.lineno,expression.end_lineno,expression.col_offset,expression.end_col_offset)
            offsets=[]
            for offset,instruction in enumerate(instructions):
                p=instruction.positions
                if instruction.opname.startswith('CALL') and (p.lineno,p.end_lineno,p.col_offset,p.end_col_offset)==position:
                    offsets.append(instruction.offset)
                    after=offset+1
                    while after<len(instructions) and instructions[after].opname=='CACHE':
                        offsets.append(instructions[after].offset);after+=1
            if not offsets:raise ValueError('original factory CALLsite required')
            events.append(dict(factory=factory,exports=exports,node=expression,offsets=frozenset(offsets)))
        if tuple(event['factory'] for event in events)!=factories+(None,):
            raise ValueError('exact ordered factory definition and footer source required')
        if any(type(node) is ast.ClassDef and node.lineno>=events[0]['node'].lineno for node in tree.body):
            raise ValueError('source classes must precede the first factory')
        for factory in factories:
            blueprint=blueprints.get(factory)
            if (blueprint is None or blueprint.co_freevars or blueprint.co_argcount or blueprint.co_kwonlyargcount
                    or blueprint.co_flags&12):raise ValueError('zero-argument source factory required')
        generated={node.name:generated_dataclass(node) for node in tree.body if type(node) is ast.ClassDef}
        schemas[name]=(code,blueprints,tree,tuple(events),dynamic,class_fields,generated)

    def canonical(module,name):
        path,_=read_source(name);package=sys.modules.get('experiments')
        if type(module) is not ModuleType or type(package) is not ModuleType:
            raise ValueError('exact canonical factory module required')
        space=vars(module);spec=space.get('__spec__');loader=space.get('__loader__')
        if (sys.modules.get(name) is not module or vars(package).get(name.rsplit('.',1)[-1]) is not module
                or space.get('__name__')!=name or space.get('__package__')!='experiments' or space.get('__file__')!=str(path)
                or type(spec) is not importlib.machinery.ModuleSpec or spec.name!=name or spec.origin!=str(path)
                or spec.loader is not loader or type(loader) is not importlib.machinery.SourceFileLoader
                or loader.name!=name or loader.path!=str(path)):
            raise ValueError('canonical pinned factory loader required')
        return space

    def mint_classes(name,space):
        # Execute only the independently pinned class statements. Their methods
        # get the original canonical globals; no offered class object is reused.
        for node in schemas[name][2].body:
            if type(node) is not ast.ClassDef:continue
            if node.keywords:raise ValueError('plain source class metaclass required')
            bases=tuple(resolve(base,space) for base in node.bases) or (object,)
            if any(type(base) is not type or dataclasses.is_dataclass(base)
                    or any('__init_subclass__' in vars(ancestor) for ancestor in base.__mro__ if ancestor is not object)
                    for base in bases):
                raise ValueError('plain source class bases without creation hooks required')
            for decorator in node.decorator_list:
                if resolve(decorator.func,space) is not dataclasses.dataclass:
                    raise ValueError('original stdlib dataclass decorator required')
            unit=ast.Module(body=[node],type_ignores=[])
            exec(compile(unit,str(directory/(name.rsplit('.',1)[-1]+'.py')),'exec',dont_inherit=True),space)
        class_states[name]=tuple((ref(space[key]),class_state(space[key])) for key in schemas[name][5])

    def class_state(kind):
        remaining=[8192];active=set()
        def observed(value,depth=0):
            remaining[0]-=1
            if remaining[0]<0 or depth>32:raise ValueError('bounded source class state required')
            value_type=type(value)
            if value_type in (str,bytes,int,float,bool,type(None)):return state.literal(value)
            if value_type is type:return ('class',ref(value))
            if value is dataclasses.MISSING:return ('stdlib_missing',)
            for label in ('_FIELD','_FIELD_CLASSVAR','_FIELD_INITVAR'):
                if value is getattr(dataclasses,label):return ('stdlib_field_kind',label)
            if value_type in (GetSetDescriptorType,MemberDescriptorType):
                return ('class_descriptor',value_type,id(value),ref(value.__objclass__),value.__name__)
            if value_type is dataclasses.Field:
                return ('field',id(value),tuple((key,observed(object.__getattribute__(value,key),depth+1))
                    for key in value_type.__slots__ if key!='__weakref__'))
            if value_type is dataclasses._DataclassParams:
                return ('dataclass_parameters',tuple((key,observed(object.__getattribute__(value,key),depth+1))
                    for key in value_type.__slots__))
            if value_type not in (tuple,list,dict,MappingProxyType):
                raise ValueError('source-specific contract required for nonliteral class state')
            if id(value) in active:raise ValueError('acyclic source class state required')
            active.add(id(value))
            try:
                payload=tuple((observed(key,depth+1),observed(part,depth+1)) for key,part in value.items()) if value_type in (
                    dict,MappingProxyType) else tuple(observed(part,depth+1) for part in value)
                return (value_type,id(value),payload)
            finally:active.remove(id(value))
        return (tuple(vars(kind)),tuple((key,observed(value)) for key,value in vars(kind).items()
            if not isinstance(value,(FunctionType,property,staticmethod,classmethod)) and not callable(value)))

    def resolve(node,space):
        if type(node) is ast.Name:
            if node.id in space:return space[node.id]
            return vars(builtins).get(node.id)
        if type(node) is ast.Attribute:
            owner=resolve(node.value,space)
            if type(owner) not in (ModuleType,type):raise ValueError('literal canonical factory alias required')
            return vars(owner).get(node.attr)
        raise ValueError('literal factory namespace path required')

    def imported(node,space):
        if type(node) is ast.Import:
            edges=tuple((alias.asname or alias.name.split('.')[0],alias.name if alias.asname else alias.name.split('.')[0],None)
                for alias in node.names)
        else:
            target=importlib.util.resolve_name('.'*node.level+(node.module or ''),'experiments') if node.level else node.module
            if not target or any(alias.name=='*' for alias in node.names):raise ValueError('explicit factory import required')
            edges=tuple((alias.asname or alias.name,target,alias.name) for alias in node.names)
        for alias,target,member in edges:
            module=sys.modules.get(target)
            if type(module) is not ModuleType:raise ValueError('canonical factory import module required')
            value=module if member is None else vars(module).get(member)
            full=target if member is None else target+'.'+member
            if type(value) is ModuleType and sys.modules.get(full) is not value:
                raise ValueError('canonical factory imported module edge required')
            project=full if type(value) is ModuleType else target
            if project.startswith('experiments.') and project not in expected:
                raise ValueError('predeclared project factory import pin required')
            if project.startswith('experiments.'):
                canonical(value if type(value) is ModuleType else module,project)
                if type(value) is FunctionType and project not in slots:
                    dependency_code,dependency_tree=dependency_sources[project]
                    declaration=next((part for part in dependency_tree.body if type(part) in (ast.FunctionDef,ast.AsyncFunctionDef)
                        and part.name==member),None)
                    if (declaration is None or value.__globals__ is not vars(module) or value.__closure__
                            or value.__code__!=function_code(dependency_code,member)):
                        raise ValueError('source-specific original imported callable required')
                    defaults(value,declaration)
            if space.get(alias) is not value:raise ValueError('original factory import edge changed')

    def marker(value,owned=True):
        if type(value) is FunctionType and owned:return ('function',state.weak_observation(value))
        if type(value) in (staticmethod,classmethod):return ('descriptor',type(value),state.weak_observation(value.__func__))
        if type(value) is property:return ('property',id(value),tuple(None if fn is None else state.weak_observation(fn)
            for fn in (value.fget,value.fset,value.fdel)))
        return ('object',ref(value))

    def compare(observed,value):
        if observed[0]=='function':state.check_weak(observed[1],value)
        elif observed[0]=='descriptor':
            if type(value) is not observed[1]:raise ValueError('original factory descriptor changed')
            state.check_weak(observed[2],value.__func__)
        elif observed[0]=='property':
            if type(value) is not property or id(value)!=observed[1]:raise ValueError('original factory property changed')
            for before,fn in zip(observed[2],(value.fget,value.fset,value.fdel)):
                if before is None:
                    if fn is not None:raise ValueError('original factory property accessor changed')
                else:state.check_weak(before,fn)
        elif observed[1]() is not value:raise ValueError('original factory object changed')

    def previous(name):
        for owner,key,observed in observations.get(name,()):
            live=owner()
            if live is None:raise ValueError('original factory definition expired')
            compare(observed,vars(live).get(key))
        for reference,before in class_states.get(name,()):
            kind=reference()
            if kind is None or class_state(kind)!=before:raise ValueError('minted source class state changed')

    def inspect(module,name,event_index):
        space=canonical(module,name);code,blueprints,tree,events,dynamic,classes,generated=schemas[name]
        line=events[event_index]['node'].lineno;allowed={_DEFINE,_REGISTER};required={};class_nodes={}
        for node in tree.body:
            if node.lineno>=line:continue
            if type(node) in (ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef):
                allowed.add(node.name);required[node.name]=node
                if type(node) is ast.ClassDef:class_nodes[node.name]=node
            elif type(node) in (ast.Import,ast.ImportFrom):
                imported(node,space);allowed.update(alias.asname or alias.name.split('.')[0] for alias in node.names)
            elif type(node) in (ast.Assign,ast.AnnAssign):
                for target in node.targets if type(node) is ast.Assign else (node.target,):
                    allowed.update(target_names(target))
        allowed.update(dynamic)
        observed={(id(owner()),key):value for owner,key,value in observations.get(name,()) if owner() is not None}
        def authored(value,qualname,node):
            if type(value) is not FunctionType or value.__code__!=blueprints.get(qualname) or value.__globals__ is not space or value.__closure__:
                raise ValueError('original plain factory source function required')
            defaults(value,node)
        for key,node in required.items():
            value=space.get(key)
            if type(node) is not ast.ClassDef:
                if (id(module),key) not in observed:authored(value,key,node)
            elif type(value) is not type or value.__module__!=name:
                raise ValueError('original source factory class required')
            else:
                bases=tuple(resolve(base,space) for base in node.bases) or (object,)
                if value.__bases__!=bases:raise ValueError('original source factory class bases required')
                for child in node.body:
                    if type(child) not in (ast.FunctionDef,ast.AsyncFunctionDef):continue
                    descriptor=vars(value).get(child.name)
                    if (id(value),child.name) in observed:continue
                    decorators=child.decorator_list
                    expected_kind=FunctionType if not decorators else {'staticmethod':staticmethod,
                        'classmethod':classmethod,'property':property}.get(entry_name(decorators[0])) if len(decorators)==1 else None
                    if type(descriptor) is not expected_kind:
                        raise ValueError('original plain factory source function or source-declared descriptor kind required')
                    parts=(descriptor.__func__,) if type(descriptor) in (staticmethod,classmethod) else (
                        tuple(fn for fn in (descriptor.fget,descriptor.fset,descriptor.fdel) if fn is not None)
                        if type(descriptor) is property else (descriptor,))
                    for fn in parts:authored(fn,node.name+'.'+child.name,child)
        for key,value in tuple(space.items()):
            if not (isinstance(value,_KINDS) or callable(value)):continue
            if key not in allowed:raise ValueError('additional factory module callable refused')
        for key in class_nodes:
            kind=space[key]
            for member,value in vars(kind).items():
                if not isinstance(value,(FunctionType,property,staticmethod,classmethod)) and not callable(value):continue
                if member in classes[key]:continue
                shape=generated[key].get(member)
                if shape is None or type(value) is not FunctionType or value.__code__!=shape[0]:
                    raise ValueError('additional factory class callable refused')
                if member=='__repr__':
                    cells=dict(zip(value.__code__.co_freevars,(cell.cell_contents for cell in value.__closure__ or ())))
                    inner=cells.get('user_function')
                    if (type(inner) is not FunctionType or inner.__code__!=shape[1]
                            or type(cells.get('repr_running')) is not set or cells['repr_running']):
                        raise ValueError('original generated dataclass repr required')
                elif value.__closure__:
                    cells=dict(zip(value.__code__.co_freevars,(cell.cell_contents for cell in value.__closure__)))
                    if any(part is not {'cls':kind,'FrozenInstanceError':dataclasses.FrozenInstanceError}.get(key_,
                            getattr(builtins,key_,None)) for key_,part in cells.items()):
                        raise ValueError('original generated dataclass closure required')
        return space

    def snapshot(module,name,virtual=()):
        result=[];space=vars(module);classes=schemas[name][5]
        owners=(module,)+tuple(value for key,value in space.items() if key in classes and type(value) is type)
        for owner in owners:
            values=dict(vars(owner))
            if owner is module:values.update(virtual)
            result.extend((ref(owner),key,marker(value,type(value) is not FunctionType or value.__module__==name))
                for key,value in values.items() if isinstance(value,_KINDS))
        return tuple(result)

    def event(module,entry,index,caller):
        if type(module) is not ModuleType:raise ValueError('exact factory source module required')
        name=vars(module).get('__name__')
        if name not in slots:raise ValueError('predeclared factory component required')
        code,_,_,events,_,_,_=schemas[name]
        selected=events[index];space=canonical(module,name)
        if (caller.f_code!=code or caller.f_globals is not space or caller.f_lasti not in selected['offsets']
                or resolve(selected['node'].func,space) is not entry):
            raise ValueError('original factory source CALLsite required')
        return name,selected

    def define(module,factory):
        if type(factory) is not str or type(module) is not ModuleType:raise ValueError('exact source factory entry required')
        name=vars(module).get('__name__')
        if name not in slots:raise ValueError('predeclared source factory required')
        family,index,factories=slots[name]
        if factory not in factories:raise ValueError('predeclared source factory name required')
        stage=factories.index(factory);name,selected=event(module,define,stage,frame_at(1))
        with lock:
            if creator!=(os.getpid(),get_ident()) or progress[family]!=[index,stage,'ready'] or (name,stage) in used:
                raise ValueError('original creator ordered one-shot factory required')
            progress[family][2]='defining';used.add((name,stage))
        try:
            previous(name);space=inspect(module,name,stage)
            if stage==0:mint_classes(name,space)
            # Never call the function object supplied by the live namespace.
            original=FunctionType(schemas[name][1][factory],space,factory)
            result=original();exports=selected['exports']
            if not exports:
                if result is not None:raise ValueError('source factory must return None without exports')
                values=()
            elif len(exports)==1:values=(result,)
            else:
                if type(result) is not tuple or len(result)!=len(exports):raise ValueError('exact source factory export arity required')
                values=result
            if any(type(value) is not FunctionType for value in values):raise ValueError('exact source factory function export required')
            observations[name]=snapshot(module,name,tuple(zip(exports,values,strict=True)))
            with lock:progress[family]=[index,stage+1,'ready']
            return result
        except BaseException:
            with lock:progress[family][2]='failed'
            raise

    def register(module):
        if type(module) is not ModuleType:raise ValueError('exact factory footer module required')
        name=vars(module).get('__name__')
        if name not in slots:raise ValueError('predeclared factory footer required')
        family,index,factories=slots[name];name,_=event(module,register,len(factories),frame_at(1))
        with lock:
            if creator!=(os.getpid(),get_ident()) or progress[family]!=[index,len(factories),'ready']:
                raise ValueError('ordered original factory footer required')
            progress[family][2]='registering'
        try:
            previous(name);inspect(module,name,len(factories));observations[name]=snapshot(module,name)
            with lock:progress[family]=[index+1,0,'ready']
        except BaseException:
            with lock:progress[family][2]='failed'
            raise

    def checked(family):
        if type(family) is not str or family not in plans:raise ValueError('exact factory family required')
        with lock:
            if creator!=(os.getpid(),get_ident()) or progress[family]!=[len(plans[family]),0,'ready']:
                raise ValueError('completed original factory definitions required')
        for name,factories in plans[family]:
            module=sys.modules.get(name);previous(name);inspect(module,name,len(factories))
        return ('source_factory_definitions_complete',family,len(plans[family]))

    return define,register,checked
