"""Pinned, weak definition registration for draft Common reader families.

This layer owns module provenance and loader activation only. A successful
activation is not a registry scope or an authenticated numerical read. The
Bootstrap coordinator must independently authorize each original private route.
"""
import ast
import dataclasses
from hashlib import sha256
import importlib.machinery
from pathlib import Path
import sys
from threading import Lock,get_ident
from types import CodeType,FunctionType,ModuleType
from weakref import ref
import os


def build_provenance(root,pins,families):
    """Bind explicit immutable source pins; callers retain the four operations.

    Production supplies a literal pinned manifest under Bootstrap's own source
    identity. This constructor cannot open a numerical scope or issue a lease.
    Each family declares bridge/witness/common names, exact activation and
    deactivation source qualnames and their runtime/route checker qualnames.
    """
    if type(root) not in (str,type(Path())) or type(pins) is not dict or type(families) is not dict:
        raise ValueError('exact builtin Common manifest data required')
    if not 1<=len(pins)<=4096 or not 1<=len(families)<=2:
        raise ValueError('bounded Common manifest required')
    for name,pin in pins.items():
        if (type(name) is not str or not name.startswith('experiments.') or len(name)>200
                or type(pin) is not str or len(pin)!=64 or any(c not in '0123456789abcdef' for c in pin)):
            raise ValueError('exact Common module name and SHA256 required')
    fields={'bridge','witness','common','graph','activate_qualname','deactivate_qualname',
        'verify_qualname','route_qualname','bridge_runtime','witness_runtime','common_runtime',
        'bridge_runtime_qualname','witness_runtime_qualname','common_runtime_qualname'}
    for name,plan in families.items():
        if type(name) is not str or type(plan) is not dict or any(type(key) is not str for key in plan) or set(plan)!=fields:
            raise ValueError('exact Common family declaration required')
        if (type(plan['graph']) is not tuple or not plan['graph'] or len(plan['graph'])>len(pins)
                or any(type(node) is not str or node not in pins for node in plan['graph'])
                or len(set(plan['graph']))!=len(plan['graph'])
                or any(type(value) is not str or not 1<=len(value)<=512 for key,value in plan.items() if key!='graph')):
            raise ValueError('bounded immutable Common family fields required')
    directory=Path(root).resolve(strict=True);guard=Lock()
    declared=tuple(sorted(pins));expected=dict(pins)
    plans={name:dict(value,graph=tuple(value['graph'])) for name,value in families.items()}
    compiled={};blueprints={};module_names={};class_names={};imports={};source_functions={}
    getframe=sys._getframe;creator=lambda:(os.getpid(),get_ident())
    for name in declared:
        path=directory/(name.rsplit('.',1)[-1]+'.py');raw=path.read_bytes()
        if type(expected[name]) is not str or sha256(raw).hexdigest()!=expected[name]:
            raise ValueError('predeclared Common source pin differs: '+name)
        code=compile(raw,str(path),'exec',dont_inherit=True);compiled[name]=code
        pending=[code];blueprint={}
        while pending:
            current=pending.pop();blueprint[current.co_qualname]=current
            pending.extend(value for value in current.co_consts if type(value) is CodeType)
        blueprints[name]=blueprint
        tree=ast.parse(raw);allowed=set();classes={};edges=[];top_functions=set()
        for node in tree.body:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                allowed.add(node.name)
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):top_functions.add(node.name)
                if isinstance(node,ast.ClassDef):
                    classes[node.name]={child.name for child in node.body if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef))}
                    for child in node.body:
                        if isinstance(child,(ast.Assign,ast.AnnAssign)):
                            targets=child.targets if isinstance(child,ast.Assign) else [child.target]
                            classes[node.name].update(target.id for target in targets if isinstance(target,ast.Name))
            elif isinstance(node,(ast.Import,ast.ImportFrom)):
                allowed.update(alias.asname or alias.name.split('.')[0] for alias in node.names)
                if isinstance(node,ast.ImportFrom) and node.module=='experiments':
                    edges.extend((alias.asname or alias.name,'experiments.'+alias.name) for alias in node.names)
            elif isinstance(node,(ast.Assign,ast.AnnAssign)):
                for target in node.targets if isinstance(node,ast.Assign) else [node.target]:
                    allowed.update(part.id for part in ast.walk(target) if isinstance(part,ast.Name))
        # Source-authored late exports and class aliases, including runtime
        # guards installed by the module's own initialization functions.
        for node in ast.walk(tree):
            if isinstance(node,ast.Attribute) and isinstance(node.ctx,ast.Store) and isinstance(node.value,ast.Name):
                if node.value.id=='module':allowed.add(node.attr)
                if node.value.id in classes:classes[node.value.id].add(node.attr)
            if isinstance(node,ast.Subscript) and isinstance(node.ctx,ast.Store) and isinstance(node.value,ast.Name):
                if node.value.id in ('namespace','globals') and isinstance(node.slice,ast.Constant) and type(node.slice.value) is str:
                    allowed.add(node.slice.value)
        module_names[name]=allowed;class_names[name]=classes;imports[name]=tuple(edges);source_functions[name]=top_functions
    roles={}
    for family,plan in plans.items():
        for role in ('bridge','witness','common'):
            name=plan[role]
            if name not in expected or name in roles:raise ValueError('disjoint predeclared Common family slots required')
            roles[name]=(family,role)
    definitions={family:{} for family in plans};used=set();active={};sequence=0;failed=set();activated=set()
    dataclass_repr=dataclasses._recursive_repr(lambda self:None).__code__

    def canonical(module,name):
        path=directory/(name.rsplit('.',1)[-1]+'.py')
        package=sys.modules.get('experiments');spec=getattr(module,'__spec__',None)
        loader=getattr(module,'__loader__',None)
        if (type(module) is not ModuleType or sys.modules.get(name) is not module
                or package is None or vars(package).get(name.rsplit('.',1)[-1]) is not module
                or module.__name__!=name or module.__package__!='experiments'
                or module.__file__!=str(path) or spec is None or spec.name!=name
                or spec.origin!=str(path) or spec.loader is not loader
                or type(loader) is not importlib.machinery.SourceFileLoader
                or loader.name!=name or loader.path!=str(path)
                or sha256(path.read_bytes()).hexdigest()!=expected[name]):
            raise ValueError('canonical pinned Common module required: '+name)
        return vars(module)

    def authored(fn,name,space,qualname=None):
        if type(fn) is not FunctionType:raise ValueError('source-authored Common function required')
        original=blueprints[name].get(qualname or fn.__code__.co_qualname)
        if original is None or fn.__code__!=original or fn.__globals__ is not space:
            raise ValueError('original Common source code and globals required: '+name)
        return fn

    def module_functions(module,name):
        space=canonical(module,name);allowed=module_names[name];classes=class_names[name]
        for field,value in tuple(space.items()):
            if type(value) is FunctionType:
                if field not in allowed:raise ValueError('additional Common module callable refused: '+field)
                if field in source_functions[name] or value.__module__==name or value.__globals__ is space:
                    authored(value,name,space,field if field in source_functions[name] else None)
            elif field in classes:
                if not isinstance(value,type) or value.__module__!=name:raise ValueError('original Common source class required')
                for member,descriptor in tuple(vars(value).items()):
                    functions=(descriptor.__func__,) if isinstance(descriptor,(staticmethod,classmethod)) else (
                        tuple(fn for fn in (descriptor.fget,descriptor.fset,descriptor.fdel) if fn is not None)
                        if isinstance(descriptor,property) else (descriptor,) if type(descriptor) is FunctionType else ())
                    for fn in functions:
                        generated='__dataclass_fields__' in vars(value) and member in (
                            '__init__','__repr__','__eq__','__hash__','__setattr__','__delattr__')
                        if generated and fn.__code__.co_filename=='<string>':continue
                        if generated and member=='__repr__' and fn.__code__ is dataclass_repr:
                            inner=dict(zip(fn.__code__.co_freevars,(cell.cell_contents for cell in fn.__closure__)))['user_function']
                            if inner.__code__.co_filename=='<string>' and inner.__globals__ is space:continue
                        if member not in classes[field]:raise ValueError('additional Common class callable refused: '+member)
                        authored(fn,name,space)
        return space

    def function_state(value):
        if isinstance(value,(staticmethod,classmethod)):return function_state(value.__func__)
        if isinstance(value,property):return tuple(function_state(fn) for fn in (value.fget,value.fset,value.fdel))
        if type(value) is not FunctionType:return None
        return (value.__code__,value.__globals__,value.__defaults__,
            value.__kwdefaults__,tuple(sorted((name,id(item)) for name,item in (value.__kwdefaults__ or {}).items())),
            value.__closure__,tuple((cell,id(cell.cell_contents)) for cell in value.__closure__ or ()),
            getattr(value,'__wrapped__',None))

    def capture(modules):
        values=[];keys=[]
        for name,module in modules.items():
            owners=[module]+[getattr(module,key) for key in class_names[name]]
            for owner in owners:
                selected=tuple(sorted((key,value) for key,value in vars(owner).items()
                    if isinstance(value,(FunctionType,ModuleType,type,property,staticmethod,classmethod))))
                keys.append((owner,tuple(key for key,_ in selected)))
                values.extend((owner,key,value,function_state(value)) for key,value in selected)
                if isinstance(owner,type):values.append((owner,'__mro__',owner.__mro__,None))
        return tuple(values),tuple(keys)

    def unchanged(inventory):
        values,keys=inventory
        for owner,key,value,state in values:
            current=getattr(owner,key) if key=='__mro__' else vars(owner).get(key)
            if current is not value or function_state(value)!=state:
                raise ValueError('active Common callable identity/default/closure changed')
        for owner,before in keys:
            current=tuple(sorted(key for key,value in vars(owner).items()
                if isinstance(value,(FunctionType,ModuleType,type,property,staticmethod,classmethod))))
            if current!=before:raise ValueError('active Common callable keyset changed')

    def frame_at(frame,name,qualname):
        module=sys.modules.get(name);space=canonical(module,name)
        if frame.f_code!=blueprints[name].get(qualname) or frame.f_globals is not space:
            raise ValueError('original Common loader frame required')
        return module

    def weak_definition(module):
        # Permanent registration must neither pin an unloadable module graph nor
        # accept a same-module re-execution that replaced its original objects.
        values=[];keys=[];ancestors=[];protocol=[]
        owners=[module]+[getattr(module,name) for name in class_names[module.__name__]]
        for owner in owners:
            owner_reference=ref(owner);selected=[]
            for key,value in vars(owner).items():
                if not isinstance(value,(FunctionType,ModuleType,type,property,staticmethod,classmethod)):continue
                selected.append(key)
                try:reference=ref(value)
                except TypeError:reference=None
                accessors=((value.__func__,) if isinstance(value,(staticmethod,classmethod)) else
                    (value.fget,value.fset,value.fdel) if isinstance(value,property) else ())
                values.append((owner_reference,key,reference,id(value),
                    tuple(None if fn is None else ref(fn) for fn in accessors)))
            keys.append((owner_reference,tuple(sorted(selected))))
            if isinstance(owner,type):
                ancestors.append((owner_reference,tuple(ref(base) for base in owner.__mro__),
                    tuple((name,id(getattr(owner,name))) for name in ('__getattribute__','__setattr__','__hash__','__eq__'))))
        for name,value in vars(module).items():
            if (name.isupper() and not name.startswith('_') or name in (
                    '_HANDOFF_NAME','_ROUTE_NAMES','_PINNED_ROUTES','_EXECUTION_FIELDS','_HOST','_FLAGS')):
                if type(value) in (str,int,float,bool,bytes,type(None),tuple,list,dict,set,frozenset):
                    protocol.append((name,freeze_protocol(value)))
        return tuple(values),tuple(keys),tuple(ancestors),tuple(protocol),ref(module)

    def freeze_protocol(value,depth=0):
        if depth>32:raise ValueError('bounded Common protocol declaration required')
        if type(value) in (str,int,float,bool,bytes,type(None)):return (type(value),value)
        if type(value) in (tuple,list,set,frozenset):
            items=tuple(freeze_protocol(item,depth+1) for item in value)
            return (type(value),frozenset(items) if type(value) in (set,frozenset) else items)
        if type(value) is dict:
            return (dict,frozenset((freeze_protocol(key,depth+1),freeze_protocol(item,depth+1)) for key,item in value.items()))
        # Non-literal dependency objects are independently covered by exact
        # callable identities; no object or module is retained by this marker.
        return (type(value).__name__,id(value))

    def original_definition(inventory):
        values,keys,ancestors,protocol,module_reference=inventory
        for owner_reference,key,reference,identity,accessors in values:
            owner=owner_reference();value=None if owner is None else vars(owner).get(key)
            if owner is None or id(value)!=identity or reference is not None and reference() is not value:
                raise ValueError('original weak Common definition changed')
            current=((value.__func__,) if isinstance(value,(staticmethod,classmethod)) else
                (value.fget,value.fset,value.fdel) if isinstance(value,property) else ())
            if len(current)!=len(accessors) or any(
                    (fn is not None if observed is None else observed() is not fn)
                    for observed,fn in zip(accessors,current)):
                raise ValueError('original weak Common descriptor changed')
        for owner_reference,before in keys:
            owner=owner_reference()
            if owner is None or tuple(sorted(key for key,value in vars(owner).items()
                    if isinstance(value,(FunctionType,ModuleType,type,property,staticmethod,classmethod))))!=before:
                raise ValueError('original weak Common callable keyset changed')
        for owner_reference,bases,methods in ancestors:
            owner=owner_reference()
            if (owner is None or len(owner.__mro__)!=len(bases)
                    or any(reference() is not base for reference,base in zip(bases,owner.__mro__))
                    or any(id(getattr(owner,name))!=identity for name,identity in methods)):
                raise ValueError('original Common class ancestry or inherited dispatch changed')
        module=module_reference()
        if module is None or any(name not in vars(module) or freeze_protocol(vars(module)[name])!=before
                for name,before in protocol):
            raise ValueError('original Common protocol constants changed')

    def register(module):
        if type(module) is not ModuleType:raise ValueError('exact Common module required')
        name=vars(module).get('__name__')
        if name not in roles:raise ValueError('predeclared Common family module required')
        family,role=roles[name];frame=getframe(1)
        space=module_functions(module,name)
        if frame.f_code!=compiled[name] or frame.f_globals is not space:
            raise ValueError('original Common source footer required')
        runtime_name=plans[family][role+'_runtime']
        authored(space.get(runtime_name),name,space,plans[family][role+'_runtime_qualname'])
        with guard:
            if (family,role) in used or family in active:raise ValueError('one Common definition registration per slot required')
            if role!='bridge':
                bridge=definitions[family].get('bridge')
                if bridge is None or bridge[0]() is None:raise ValueError('original bridge footer must register first')
            definitions[family][role]=(ref(module),weak_definition(module));used.add((family,role))
        return None

    def inspect_graph(family):
        plan=plans[family];modules={name:sys.modules.get(name) for name in declared}
        for role in ('bridge','witness','common'):
            observed=definitions[family].get(role);module=modules[plan[role]]
            if observed is None or observed[0]() is not module:raise ValueError('original registered Common definition required')
            original_definition(observed[1])
        selected={}
        for name in plan['graph']:
            module=modules[name];space=module_functions(module,name);selected[name]=module
            for alias,target in imports[name]:
                if target in expected and space.get(alias) is not modules[target]:
                    raise ValueError('pinned typed Common import edge differs')
        bridge=selected[plan['bridge']];witness=selected[plan['witness']];common=selected[plan['common']]
        if witness.operation_bridge is not bridge or common.witness is not witness:
            raise ValueError('independent Common family bridge edge differs')
        verify=authored(bridge._VERIFY_LEASE,plan['bridge'],vars(bridge),plan['verify_qualname'])
        route=authored(bridge._VERIFY_REGISTRY_ROUTE,plan['bridge'],vars(bridge),plan['route_qualname'])
        cells=dict(zip(route.__code__.co_freevars,(cell.cell_contents for cell in route.__closure__ or ())))
        if cells.get('verify') is not verify:raise ValueError('original private bridge lease checker required')
        runtime=vars(bridge)[plan['bridge_runtime']]
        runtime();vars(witness)[plan['witness_runtime']]();vars(common)[plan['common_runtime']]()
        return selected,route

    def activate(module):
        nonlocal sequence
        if type(module) is not ModuleType:raise ValueError('exact Common module required')
        name=vars(module).get('__name__')
        if name not in roles or roles[name][1]!='bridge':raise ValueError('original Common bridge activation required')
        family,_=roles[name];plan=plans[family];frame=getframe(1)
        frame_at(frame,name,plan['activate_qualname'])
        reservation=dict(state='activating',creator=creator(),token=object())
        with guard:
            if family in active:raise ValueError('one active Common loader generation required')
            if family in failed or family in activated:raise ValueError('Common loader generation requires a fresh family')
            active[family]=reservation
        route=None
        try:
            modules,route=inspect_graph(family)
            # Reserve before any callback to the bridge. On partial mutation,
            # the original source checker must implement activation_abort.
            route('activate',None,frame)
            inventory=capture(modules)
            with guard:
                if active.get(family) is not reservation:raise ValueError('original activation reservation required')
                sequence+=1;activated.add(family)
                reservation.update(state='active',modules=modules,route=route,generation=sequence,inventory=inventory)
        except BaseException as primary:
            abort_complete=False
            try:
                if route is not None:route('activation_abort',None,frame)
                abort_complete=True
            except BaseException:
                # Retain the exact original capsule and its bounded family
                # slot until the original loader can retry rollback.
                try:
                    namespace=vars(BaseException)['__dict__'].__get__(primary)
                    notes=namespace.get('__notes__')
                    if notes is None:namespace['__notes__']=['Common activation rollback remains pending']
                    elif type(notes) is list and len(notes)<16:notes.append('Common activation rollback remains pending')
                except BaseException:pass
            finally:
                with guard:
                    failed.add(family)
                    if abort_complete:
                        if active.get(family) is reservation:del active[family]
                    else:reservation.update(state='activation_cleanup_pending',modules=modules,route=route)
                if abort_complete:reservation.clear()
            raise
        return None

    def checked_row(family):
        if type(family) is not str or family not in plans:raise ValueError('exact declared Common family required')
        with guard:row=active.get(family)
        if row is None or row['state']!='active' or row['creator']!=creator():
            raise ValueError('active original creator Common loader required')
        unchanged(row['inventory'])
        selected,route=inspect_graph(family)
        if route is not row['route'] or any(selected[name] is not module for name,module in row['modules'].items()):
            raise ValueError('original active Common loader graph required')
        return row

    def checked(family):
        row=checked_row(family)
        # Observations contain only immutable scalar data. Retaining one cannot
        # mutate activation or keep any module/function/closure alive.
        return ('active_common_loader',family,row['generation'],*row['creator'])

    def deactivate(module):
        if type(module) is not ModuleType:raise ValueError('exact Common module required')
        name=vars(module).get('__name__')
        if name not in roles or roles[name][1]!='bridge':raise ValueError('original Common bridge deactivation required')
        family,_=roles[name];plan=plans[family];frame=getframe(1)
        frame_at(frame,name,plan['deactivate_qualname'])
        with guard:row=active.get(family)
        if row is None:return None
        if row['state'] not in ('active','activation_cleanup_pending','deactivation_cleanup_pending') or row['creator']!=creator() or row['modules'].get(name) is not module:
            raise ValueError('original Common deactivation creator required')
        with guard:
            if active.get(family) is not row or row['state'] not in ('active','activation_cleanup_pending','deactivation_cleanup_pending'):
                raise ValueError('original active deactivation reservation required')
            retrying=row['state']=='activation_cleanup_pending'
            row['state']='deactivating'
        complete=False
        try:
            row['route']('activation_abort' if retrying else 'deactivate',None,frame)
            complete=True
        except BaseException:
            with guard:
                failed.add(family);row['state']='activation_cleanup_pending' if retrying else 'deactivation_cleanup_pending'
            raise
        finally:
            if complete:
                with guard:
                    if active.get(family) is row:del active[family]
                row.clear()
        return None

    return register,activate,deactivate,checked
