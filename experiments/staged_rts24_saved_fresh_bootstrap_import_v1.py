"""Versioned B_S import-only boundary for the held bootstrap namespace."""
import ast
from hashlib import sha256
import importlib
from importlib import util,machinery
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import get_ident,RLock
from types import ModuleType,FunctionType,CodeType
ROOT=Path('D:/CUHKSZ/Research Project/electricity-grid')
EXE=Path('D:/Miniconda3/envs/compute/python.exe')
def require(value,message):
    if not value:raise ValueError(message)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def parse(raw):return json.loads(raw)
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def digest(value):return sha256(canonical(value)).hexdigest()

def freeze_adapter_roots(adapter,raw,runtime):
    """Authenticate direct source roots; freeze their observed contents/identities."""
    namespace=vars(adapter);tree=ast.parse(raw);unit=compile(raw,str(ROOT/'src/staged_rts24_saved_fresh_adoption_v1.py'),'exec',dont_inherit=True,optimize=0)
    expected_modules={'prefix':'src.staged_rts24_saved_prefix_replay_v1','journal':'src.staged_rts24_journal_v2'}
    for name,module_name in expected_modules.items():
        require(type(namespace[name]) is ModuleType and sys.modules.get(module_name) is namespace[name],'adapter imported module root differs')
    prefix=namespace['prefix']
    require(all(namespace[name] is vars(prefix)[name] for name in ('core','codec','mechanical','ROOT'))
        and namespace['require'] is vars(namespace['codec'])['require'],'adapter direct imported roots differ')
    require(namespace['ROOT']==ROOT and namespace['P1']==ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
        and namespace['ANCHOR']==namespace['P1'].parent/'p1_execution_review_01/postcheck_03.stdout.json','adapter fixed paths differ')
    sources=tuple(sorted(dict(runtime._sources)))
    extra=('src/staged_rts24_saved_fresh_adoption_v1.py','experiments/staged_rts24_saved_fresh_adoption_v1.py',
        'tests/test_staged_rts24_saved_fresh_adoption_v1.py','docs/plan/staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md')
    require(namespace['SOURCES']==sources and namespace['E_SOURCES']==tuple(n for n in sources if n not in extra),'adapter source selection differs')
    for node in tree.body:
        if type(node) is ast.Assign and type(node.value) is ast.Constant:
            require(len(node.targets)==1 and namespace[node.targets[0].id]==node.value.value,'adapter source constant differs')
        if type(node) is ast.Assign and any(type(t) is ast.Name and t.id=='GATES' for t in node.targets):
            expected={k.arg:ast.literal_eval(k.value) for k in node.value.keywords}
            require(namespace['GATES']==expected,'adapter initial gates differ')
        if type(node) is not ast.ClassDef:continue
        cls=namespace[node.name];compiled=next(c for c in unit.co_consts if type(c) is CodeType and c.co_name==node.name)
        require(type(cls) is type and cls.__module__==adapter.__name__ and cls.__name__==cls.__qualname__==node.name,'adapter source class differs')
        require(cls.__bases__==((ValueError,) if node.name=='ReplayUnresolved' else (object,)),'adapter class bases differ')
        for child in node.body:
            if type(child) is ast.FunctionDef:
                code=next(c for c in compiled.co_consts if type(c) is CodeType and c.co_name==child.name);fn=vars(cls)[child.name]
                require(type(fn) is FunctionType and fn.__code__==code and fn.__globals__ is namespace and fn.__defaults__ is None
                    and fn.__kwdefaults__ is None and fn.__closure__ is not None and fn.__closure__[0].cell_contents is cls,'adapter class source method differs')
        if node.name=='HeldInput':
            fields=tuple(child.target.id for child in node.body if type(child) is ast.AnnAssign)
            require(tuple(vars(cls)['__dataclass_fields__'])==fields and vars(cls)['__dataclass_params__'].frozen is True,'adapter dataclass shape differs')
    reader=runtime._namespace._graph_plan;image,objects=reader[0](reader[1],reader[2],'held_adapter_direct_graph',reader[3])(adapter)
    return (reader,image,objects)

def check_adapter_roots(adapter,proof):
    reader,expected,original=proof
    actual,objects=reader[0](reader[1],reader[2],'held_adapter_direct_graph_bookend',reader[3])(adapter)
    require(actual==expected and len(objects)==len(original) and all(a is b for a,b in zip(objects,original)),'adapter direct globals or class graph changed')


def open_bootstrap_import_boundary(policy_raw,runtime):
    runtime.entry();profile=parse(policy_raw);data=_saved_import_inputs(policy_raw)
    require(profile['schema']=='staged_saved_F_bootstrap_dependency_import_policy_v1','versioned B_S policy required')
    require(sys.getprofile() is None and sys.gettrace() is None and set(sys._current_frames())=={get_ident()},'single unprofiled B_S thread required')
    entry=profile['allowed_entry_module'];module=runtime._namespace.module
    require(sys.modules.get(entry['name']) is module and Path(module.__file__)==Path(entry['path']) and module is not sys.modules['__main__'],'exact held ENTRY namespace required')
    require(not any(name!=entry['name'] and any(name==p or name.startswith(p+'.') for p in profile['required_cold_prefixes']) for name in sys.modules),'B_S dependencies must be cold')
    require(tuple((v.__module__,v.__name__) for v in sys.meta_path)==(('_frozen_importlib','BuiltinImporter'),('_frozen_importlib','FrozenImporter'),('_frozen_importlib_external','PathFinder')),'exact baseline B3 required')
    require(tuple(sys.path)==tuple(profile['initial_paths']) and sys.flags.safe_path and sys.flags.no_site and sys.flags.no_user_site,'exact B_S startup paths/flags required')
    guard=object.__new__(BootstrapImportBoundary);token=object();finder_plan=_saved_import_finder_plan(data,profile)
    def audit_hook(event,args):guard._audit(event,args,token)
    creator=(os.getpid(),get_ident());namespace=globals();bindings=[]
    for name in ('sys','os','subprocess','get_ident','ROOT','EXE','_READ_FILE','pin','require','sha256','digest','Path','canonical','parse','_saved_import_inputs','_saved_import_finder_plan','freeze_adapter_roots','check_adapter_roots','ModuleType','FunctionType','CodeType','importlib','util','machinery'):
        value=namespace[name];function=type(value) is FunctionType
        bindings.append((name,value,value.__code__ if function else None,value.__defaults__ if function else None,canonical(value.__kwdefaults__) if function else None,value.__closure__ if function else None))
    attrs=[(sys,name,getattr(sys,name)) for name in ('addaudithook','audit','getprofile','gettrace','setprofile','settrace','modules','_current_frames','meta_path','path_hooks','path','path_importer_cache','version','executable','dont_write_bytecode')]
    attrs.append((sys.modules['builtins'],'__import__',sys.modules['builtins'].__import__))
    attrs.extend((m,name,getattr(m,name)) for m,names in ((importlib,('util','machinery','import_module')),(util,('find_spec','spec_from_loader')),(machinery,('ModuleSpec','FileFinder'))) for name in names)
    own=tuple((name,fn,fn.__code__,fn.__defaults__,canonical(fn.__kwdefaults__),fn.__closure__) for name,fn in vars(BootstrapImportBoundary).items() if type(fn) is FunctionType)
    units={path:compile(raw,path,'exec',dont_inherit=True,optimize=0) for path,raw in data.items() if path.endswith('.py')};pool=[]
    def walk(code):
        pool.append(code)
        for value in code.co_consts:
            if type(value) is CodeType:walk(value)
    for unit in units.values():walk(unit)
    codes=tuple(next(c for c in pool if c.co_qualname==name and c.co_firstlineno==line) for name,line,_ in profile['optional_stack'])
    owner=(creator,audit_hook,token,audit_hook.__code__);owner_commit=digest((creator,id(audit_hook),id(audit_hook.__code__),id(token)))
    values=dict(_profile_raw=policy_raw,_creator=creator,_namespace=namespace,_global_bindings=tuple(bindings),_attribute_bindings=tuple(attrs),_own_bindings=own,
        _owner=owner,_owner_commit=owner_commit,_lock=RLock(),_codes=codes,_numpy_path=next(p for p in profile['external_sources'] if p.replace('\\','/').endswith('/numpy/testing/_private/utils.py')),
        _numpy_state=None,_paths=tuple(os.path.normcase(os.path.abspath(p)) for p in profile['protected_open_roots'].values()),
        _event_sets=(tuple(profile['process_events']),tuple(profile['process_event_prefixes']),tuple(profile['mutation_events'])),
        _import_machinery=(tuple(map(id,sys.meta_path)),tuple(map(id,sys.path_hooks)),tuple(sys.path),id(sys.path_importer_cache),id(sys.modules)),
        _machinery_base=(tuple(sys.meta_path),tuple(sys.path_hooks),tuple(sys.path),sys.meta_path,sys.path_hooks,sys.path,sys.path_importer_cache,sys.modules,importlib,util,machinery),
        _finder_plan=finder_plan,_finder_bindings=(),_finder_authenticated=(),_observed_stage=0,_authenticated_stage=0,
        _state=('NEW',True,0,0,0,0,False,''),_internal=None,_busy=False,_adapter=None,_adapter_bindings=(),_source_raw=None,_failure=None,_first_error=None,_req=require,
        _runtime=runtime,_path_stage=0,_load_started=False,_cache_initial=tuple(sys.path_importer_cache.items()),_module_initial=tuple(sys.modules.items()),_policy_profile=profile,
        _admitted_paths=tuple(profile['admitted_paths']),_runtime_bindings=(),_retention=(),_handoff_seen=0,_adapter_graph=None)
    for name,value in values.items():object.__setattr__(guard,name,value)
    object.__setattr__(guard,'_commit',digest(guard._image()));object.__setattr__(guard,'_state',('INSTALLING',guard._state[1],guard._state[2],guard._state[3],guard._state[4],guard._state[5],guard._state[6],guard._state[7]));object.__setattr__(guard,'_commit',digest(guard._image()))
    runtime.own_pending_boundary(guard)
    try:
        sys.addaudithook(audit_hook);sys.audit('electricity_grid.saved_import.installation',token)
        require(guard._state[3]==1,'B_S audit installation not observed');object.__setattr__(guard,'_state',('ACTIVE',guard._state[1],guard._state[2],guard._state[3],guard._state[4],guard._state[5],guard._state[6],guard._state[7]));object.__setattr__(guard,'_commit',digest(guard._image()));guard._entry()
        runtime.activate_boundary();return guard
    except BaseException as primary:
        try:guard.close(primary)
        except BootstrapImportUnresolved:raise
        raise BootstrapImportUnresolved(guard,primary,()) from primary


def load_bootstrap_adapter(runtime,boundary):
    require(runtime._boundary is boundary and boundary.phase()=='PATH6','exact path-admitted runtime boundary required')
    expected=runtime.source_bookend();boundary.begin_import()
    adapter=importlib.import_module('src.staged_rts24_saved_fresh_adoption_v1')
    boundary.authenticate_machinery()
    numpy_module=sys.modules.get('numpy.testing._private.utils')
    require(type(numpy_module) is ModuleType and Path(numpy_module.__file__).absolute()==Path(boundary._numpy_path) and numpy_module._SUPPORTS_SVE is False,'actual NumPy CPU fallback differs')
    object.__setattr__(boundary,'_numpy_state',(numpy_module,False));object.__setattr__(boundary,'_commit',digest(boundary._image()))
    require(type(adapter) is ModuleType and Path(adapter.__file__).absolute()==ROOT/'src/staged_rts24_saved_fresh_adoption_v1.py','actual adapter module path differs')
    raw=runtime.source_bytes('src/staged_rts24_saved_fresh_adoption_v1.py')
    unit=compile(raw,str(ROOT/'src/staged_rts24_saved_fresh_adoption_v1.py'),'exec',dont_inherit=True,optimize=0)
    nodes=[node for node in ast.parse(raw).body if type(node) is ast.FunctionDef]
    expected_functions={c.co_name:c for c in unit.co_consts if type(c) is CodeType and c.co_name in {node.name for node in nodes}}
    require(len(nodes)==len(expected_functions)==13,'fixed thirteen adapter function roots required')
    bindings=[]
    for node in nodes:
        name=node.name;code=expected_functions[name];fn=vars(adapter).get(name)
        defaults=tuple(ast.literal_eval(value) for value in node.args.defaults) or None
        kw={arg.arg:ast.literal_eval(value) for arg,value in zip(node.args.kwonlyargs,node.args.kw_defaults) if value is not None} or None
        require(not node.decorator_list and type(fn) is FunctionType and fn.__globals__ is vars(adapter) and fn.__code__==code
            and fn.__defaults__==defaults and fn.__kwdefaults__==kw and fn.__closure__ is None,'held adapter source function differs')
        bindings.append((name,fn,fn.__code__,fn.__defaults__,canonical(fn.__kwdefaults__),fn.__closure__))
    object.__setattr__(boundary,'_adapter',adapter);object.__setattr__(boundary,'_adapter_bindings',tuple((n,fn,code) for n,fn,code,*_ in bindings))
    object.__setattr__(boundary,'_runtime_bindings',tuple(bindings));object.__setattr__(boundary,'_commit',digest(boundary._image()))
    proof=freeze_adapter_roots(adapter,raw,runtime);object.__setattr__(boundary,'_adapter_graph',proof);object.__setattr__(boundary,'_commit',digest(boundary._image()))
    runtime.source_bookend();object.__setattr__(boundary,'_source_raw',canonical(expected));object.__setattr__(boundary,'_commit',digest(boundary._image()))
    require(all(name in sys.modules and sys.modules[name] is module for name,module in boundary._module_initial),'initial B_S modules changed')
    require(len(sys.modules)<=4096,'runtime module retention cap')
    object.__setattr__(boundary,'_retention',tuple(sys.modules.items()));object.__setattr__(boundary,'_commit',digest(boundary._image()))
    sys.audit('electricity_grid.B_S.adapter_authenticated',adapter)
    boundary.close();return adapter,boundary._runtime_bindings,boundary._retention
class BootstrapImportRejected(RuntimeError): pass


class _SavedImportCPUQueryDenied(OSError): pass


class _SavedImportFrameMarker(Exception): pass


class BootstrapImportUnresolved(RuntimeError):
    def __init__(self,boundary,primary,cleanup):
        self.boundary,self.primary,self.cleanup=boundary,primary,tuple(cleanup)
        super().__init__('successor dependency import did not complete')
    def __reduce__(self):raise TypeError('import failure retains local state')


def _saved_import_inputs(policy_raw):
    require(type(policy_raw) is bytes and len(policy_raw)==4745 and sha256(policy_raw).hexdigest()=='4b731fc38ed2b52bff727acf0b02e4b8da7396cb17f2354225b34348155d9e9c','fixed import input policy required')
    profile=parse(policy_raw)
    require(Path(sys.executable).absolute()==Path(profile['executable_path']) and sys.version==profile['python']
        and sys.dont_write_bytecode is True and sys.flags.optimize==0,'pinned import runtime and -B required')
    expected={profile['executable_path']:profile['executable_pin'],**profile['external_sources']}
    data={name:_READ_FILE(name,expected[name],links=True) for name in expected}
    require({name:pin(value) for name,value in data.items()}==expected,'import external source/runtime pin differs')
    return data


def _saved_import_finder_plan(data,profile):
    """Compile fixed sources without executing them; all returned plan rows are tuples."""
    import ast
    result=[]
    for rule in profile['machinery_transition']['finders']:
        path=next(p for p in data if p.replace('\\','/').endswith('/pyomo/common/'+rule['module'].rsplit('.',1)[1]+'.py'))
        tree=ast.parse(data[path]);unit=compile(data[path],path,'exec',dont_inherit=True,optimize=0)
        def methods(node,code):
            values=[]
            for fn in node.body:
                if type(fn) is not ast.FunctionDef:continue
                require(not fn.decorator_list and not fn.args.kwonlyargs and fn.args.vararg is None and fn.args.kwarg is None,'fixed finder method signature required')
                require(all(type(d) is ast.Constant and d.value is None for d in fn.args.defaults),'fixed finder defaults required')
                candidates=[c for c in code.co_consts if type(c) is CodeType and c.co_name==fn.name]
                require(len(candidates)==1,'unique fixed finder method required')
                values.append((fn.name,candidates[0],len(fn.args.defaults)))
            return tuple(values)
        classes=[]
        for name in (rule['finder'],rule['loader']):
            nodes=[n for n in tree.body if type(n) is ast.ClassDef and n.name==name]
            codes=[c for c in unit.co_consts if type(c) is CodeType and c.co_name==name]
            require(len(nodes)==len(codes)==1 and not nodes[0].bases and not nodes[0].decorator_list and not nodes[0].keywords,'fixed plain finder class required')
            registry=rule['registry'] if name==rule['finder'] else None
            assigned=[n for n in nodes[0].body if type(n) is ast.Assign]
            require((not assigned) if registry is None else len(assigned)==1 and len(assigned[0].targets)==1
                and type(assigned[0].targets[0]) is ast.Name and assigned[0].targets[0].id==registry
                and type(assigned[0].value) is ast.Dict and not assigned[0].value.keys,'fixed finder registry definition required')
            classes.append((name,ast.get_docstring(nodes[0],clean=False),registry,methods(nodes[0],codes[0])))
        extra=[]
        if rule['tag']=='M':
            fn=next(n for n in tree.body if type(n) is ast.FunctionDef and n.name=='deprecation_warning')
            code=next(c for c in unit.co_consts if type(c) is CodeType and c.co_name==fn.name)
            require(not fn.decorator_list and all(type(d) is ast.Constant and d.value is None for d in fn.args.defaults),'fixed warning binding required')
            extra.append((fn.name,code,len(fn.args.defaults)))
        result.append((rule['tag'],rule['module'],path,rule['finder'],rule['loader'],rule['registry'],rule['singleton'],tuple(classes),tuple(extra)))
    require(tuple(r[0] for r in result)==('M','D'),'fixed finder order required')
    return tuple(result)


class BootstrapImportBoundary:
    __slots__=('_profile_raw', '_creator', '_namespace', '_global_bindings', '_attribute_bindings', '_own_bindings', '_owner', '_owner_commit', '_lock', '_codes', '_numpy_path', '_numpy_state', '_paths', '_event_sets', '_import_machinery', '_machinery_base', '_finder_plan', '_finder_bindings', '_finder_authenticated', '_observed_stage', '_authenticated_stage', '_state', '_internal', '_busy', '_adapter', '_adapter_bindings', '_source_raw', '_commit', '_failure', '_first_error', '_req', '_runtime', '_path_stage', '_load_started', '_cache_initial', '_module_initial', '_policy_profile', '_admitted_paths', '_runtime_bindings', '_retention', '_handoff_seen', '_adapter_graph')
    def __setattr__(self,name,value):raise AttributeError("import boundary fields are frozen")
    def __delattr__(self,name):raise AttributeError("import boundary fields are frozen")
    def claim_pending(self,runtime):
        self._entry()
        self._req(self._runtime is runtime and runtime._boundary is None and runtime._phase=='ADOPTED'
            and self._state==('INSTALLING',True,0,0,0,0,False,'') and self._path_stage==0 and not self._load_started
            and self._handoff_seen==0 and self._adapter is None and not self._runtime_bindings and not self._retention,
            'exact prepared pending boundary required')
        creator,callback,token=self._ownership()
        self._req(callback.__globals__ is self._namespace and callback.__code__.co_freevars==('guard','token')
            and callback.__closure__[0].cell_contents is self and callback.__closure__[1].cell_contents is token,
            'original pending callback closure required')
        return self
    def _check_cache(self):
        current=sys.path_importer_cache;before=dict(self._cache_initial)
        for key,value in before.items():
            self._req(key in current and current[key] is value ,'predecessor importer cache changed')
        roots=(str(ROOT),str(EXE.parent))
        for key,value in current.items():
            if key in before:continue
            self._req(type(key) is str and os.path.isabs(key) and any(Path(key).is_relative_to(Path(root)) for root in roots),'importer cache key outside admitted roots')
            self._req(value is None or type(value) is machinery.FileFinder and value.path==key,'new importer cache kind differs')
    def phase(self):
        state=self._state[0]
        if state!='ACTIVE':return state
        if self._authenticated_stage==2:return 'AUTHENTICATED'
        if self._observed_stage==2:return 'D_SEEN'
        if self._observed_stage==1:return 'M_SEEN'
        if self._load_started:return 'IMPORTING'
        return 'ACTIVE_B3' if self._path_stage==0 else 'PATH6'
    def admit_paths(self):
        self._entry();self._req(self.phase()=='ACTIVE_B3' and self._runtime._audit_handed_off,'active handed-off B_S path transition required')
        self._req(tuple(sys.path)==tuple(self._policy_profile['initial_paths']),'fixed B_S initial paths required')
        sys.audit('electricity_grid.B_S.path_prepared',self)
        object.__setattr__(self,'_path_stage',1);sys.path.extend(self._admitted_paths[4:]);object.__setattr__(self,'_commit',digest(self._image()))
        sys.audit('electricity_grid.B_S.path_committed',self);return self._entry()
    def begin_import(self):
        self._entry();self._req(self.phase()=='PATH6' and not self._load_started,'single B_S import episode required')
        object.__setattr__(self,'_load_started',True);object.__setattr__(self,'_commit',digest(self._image()));sys.audit('electricity_grid.B_S.import_begin',self)
        return self
    def profile_raw(self):
        self._entry();self._req(self._state[0]=='CLOSED','completed import profile required')
        modules=[]
        for name,module in sorted(sys.modules.items()):
            if type(module) is ModuleType:
                namespace=vars(module);spec=namespace.get('__spec__');loader=namespace.get('__loader__')
                origin=getattr(spec,'origin',None) if type(spec) is machinery.ModuleSpec else None
                modules.append((name,'module',namespace.get('__file__'),origin,type(loader).__module__+'.'+type(loader).__qualname__))
            else:modules.append((name,'opaque',type(module).__module__+'.'+type(module).__qualname__))
        self._req(len(modules)<=4096 and len(sys.path_importer_cache)<=4096,'B_S retention observation cap')
        cache=tuple((key,'None' if value is None else type(value).__module__+'.'+type(value).__qualname__) for key,value in sorted(sys.path_importer_cache.items()))
        return canonical(dict(schema='staged_saved_F_B_S_import_observation_v1',authority='DRAFT_NONAUTHORITATIVE',
            modules=modules,cache=cache,paths=tuple(sys.path),finder_types=tuple(type(v).__module__+'.'+type(v).__qualname__ if not isinstance(v,type) else v.__module__+'.'+v.__qualname__ for v in sys.meta_path),
            machinery_observed=self._observed_stage,machinery_authenticated=self._authenticated_stage,
            optional_attempts=self._state[2],loaded_python_graph_attested=False,registry_contents_verified=False,native_behavior_verified=False))
    _profile_raw: bytes
    _creator: tuple
    _namespace: object
    _global_bindings: tuple
    _attribute_bindings: tuple
    _own_bindings: tuple
    _owner: tuple
    _owner_commit: str
    _lock: object
    _codes: tuple
    _numpy_path: str
    _numpy_state: object
    _paths: tuple
    _event_sets: tuple
    _import_machinery: tuple
    _machinery_base: tuple
    _finder_plan: tuple
    _finder_bindings: tuple
    _finder_authenticated: tuple
    _observed_stage: int
    _authenticated_stage: int
    _state: tuple
    _internal: object
    _busy: bool
    _adapter: object
    _adapter_bindings: tuple
    _source_raw: object
    _commit: str
    _failure: object
    _first_error: object
    _req: object
    def __new__(cls,*a,**k):raise TypeError('open the fixed successor import policy explicitly')
    def __init_subclass__(cls,**kw):raise TypeError('exact successor import policy type required')
    def _image(self):
        return (id(self._adapter_graph),id(self._runtime_bindings),id(self._retention),self._handoff_seen,id(self._runtime),self._path_stage,self._load_started,id(self._cache_initial),id(self._module_initial),id(self._policy_profile),self._admitted_paths,pin(self._profile_raw),self._creator,id(self._namespace),
            tuple((n,id(v),id(code),id(defaults),pin(kw) if type(kw) is bytes else None,id(closure)) for n,v,code,defaults,kw,closure in self._global_bindings),
            tuple((id(m),n,id(v)) for m,n,v in self._attribute_bindings),
            tuple((n,id(fn),id(code),id(defaults),pin(kw),id(closure)) for n,fn,code,defaults,kw,closure in self._own_bindings),
            self._owner_commit,id(self._lock),tuple(id(code) for code in self._codes),self._numpy_path,
            None if self._numpy_state is None else (id(self._numpy_state[0]),self._numpy_state[1]),self._paths,self._event_sets,self._import_machinery,
            id(self._machinery_base),id(self._finder_plan),id(self._finder_bindings),id(self._finder_authenticated),self._observed_stage,self._authenticated_stage,
            self._state,id(self._adapter),tuple((n,id(fn),id(code)) for n,fn,code in self._adapter_bindings),
            pin(self._source_raw) if self._source_raw is not None else None,id(self._failure),id(self._first_error),id(self._req))
    def _ownership(self):
        creator,callback,token,code=self._owner
        self._req(creator==self._creator and self._owner_commit==digest((creator,id(callback),id(code),id(token))),
            'import guard ownership changed')
        return creator,callback,token
    def _finder_class_shape(self,cls,spec):
        name,doc,registry,methods=spec
        self._req(type(cls) is type and cls.__bases__==(object,) and cls.__name__==cls.__qualname__==name,'fixed finder class differs')
        namespace=vars(cls);expected={'__module__','__doc__','__dict__','__weakref__',*(m[0] for m in methods)}
        if registry is not None:expected.add(registry)
        self._req(set(namespace) in (expected,expected|{'__qualname__'}) and namespace['__doc__']==doc,'fixed finder class fields differ')
        functions=tuple((name,namespace[name]) for name,code,count in methods)
        self._req(all(type(fn) is FunctionType for name,fn in functions),'fixed finder functions required')
        return functions
    def _hold_finder(self,plan,finder):
        tag,module_name,path,finder_name,loader_name,registry_name,singleton,classes,extra=plan
        module=sys.modules.get(module_name)
        self._req(type(module) is ModuleType,'fixed finder module required');namespace=vars(module)
        self._req(type(namespace.get('__file__')) is str and Path(namespace['__file__']).absolute()==Path(path),'fixed finder module path differs')
        cls=namespace.get(finder_name)
        self._req(type(finder) is cls and type(vars(finder)) is dict and not vars(finder),'exact empty finder instance required')
        held=[]
        for spec in classes:
            current=namespace.get(spec[0]);functions=self._finder_class_shape(current,spec)
            self._req(vars(current)['__module__']==module_name,'fixed finder class module differs')
            held.append((spec,current,functions))
        registry=vars(cls)[registry_name];self._req(type(registry) is dict,'finder registry object required')
        names=('sys','importlib',finder_name,loader_name)+(('NOTSET','deprecation_warning') if tag=='M' else (singleton,))
        self._req(all(n in namespace for n in names) and namespace['sys'] is sys and namespace['importlib'] is self._machinery_base[8],'finder globals differ')
        if singleton is not None:self._req(namespace[singleton] is finder,'finder singleton differs')
        return (plan,module,namespace,finder,registry,tuple(held),tuple((n,namespace[n]) for n in names))
    def _check_finder_structure(self,binding):
        plan,module,namespace,finder,registry,classes,globals_held=binding
        self._req(sys.modules.get(plan[1]) is module and vars(module) is namespace,'finder module identity differs')
        self._req(type(namespace.get('__file__')) is str and Path(namespace['__file__']).absolute()==Path(plan[2]),'finder module path changed')
        self._req(type(finder) is classes[0][1] and type(vars(finder)) is dict and not vars(finder),'finder instance changed')
        self._req(vars(type(finder)).get(plan[5]) is registry,'finder registry identity changed')
        for name,value in globals_held:self._req(namespace.get(name) is value,'finder global identity changed')
        for spec,cls,functions in classes:
            self._req(namespace.get(spec[0]) is cls and vars(cls)['__module__']==plan[1],'finder class identity changed')
            current=self._finder_class_shape(cls,spec)
            self._req(all(n==m and fn is original for (n,fn),(m,original) in zip(current,functions)),'finder method identity changed')
    def _observe_machinery(self):
        try:
            base=self._machinery_base
            self._req(sys.meta_path is base[3] and sys.path_hooks is base[4] and sys.path is base[5]
                and sys.path_importer_cache is base[6] and sys.modules is base[7],'machinery container changed')
            self._req(tuple(map(id,sys.path_hooks))==tuple(map(id,base[1])) and tuple(sys.path)==(base[2] if self._path_stage==0 else self._admitted_paths),'machinery hooks/path changed')
            live=tuple(sys.meta_path);original=base[0];stage=self._observed_stage
            same=lambda a,b:len(a)==len(b) and all(x is y for x,y in zip(a,b))
            expected=original if stage==0 else (*original,self._finder_bindings[0][3]) if stage==1 else (self._finder_bindings[1][3],*original,self._finder_bindings[0][3])
            if not same(live,expected):
                if stage==0 and len(live)==len(original)+1 and same(live[:-1],original):
                    binding=self._hold_finder(self._finder_plan[0],live[-1])
                    object.__setattr__(self,'_finder_bindings',(binding,));object.__setattr__(self,'_observed_stage',1);object.__setattr__(self,'_commit',digest(self._image()));sys.audit('electricity_grid.B_S.finder_stage',1)
                elif stage==1 and len(live)==len(original)+2 and same(live[1:-1],original) and live[-1] is self._finder_bindings[0][3]:
                    binding=self._hold_finder(self._finder_plan[1],live[0])
                    object.__setattr__(self,'_finder_bindings',(*self._finder_bindings,binding));object.__setattr__(self,'_observed_stage',2);object.__setattr__(self,'_commit',digest(self._image()));sys.audit('electricity_grid.B_S.finder_stage',2)
                else:self._fault('machinery_sequence')
            for binding in self._finder_bindings:self._check_finder_structure(binding)
        except BootstrapImportRejected:raise
        except BaseException as error:self._fault('machinery_binding',error)
    def _check_finder_authentication(self):
        try:
            if self._busy:self._fault('finder_authentication_busy')
            self._req(self._authenticated_stage in (0,2),'finder authentication stage differs')
            if self._authenticated_stage==0:
                self._req(not self._finder_authenticated,'pending finder code bindings differ');return
            self._req(self._observed_stage==2 and self._finder_authenticated,'authenticated finder sequence differs')
            for fn,code,defaults,namespace,expected,count in self._finder_authenticated:
                self._req(fn.__globals__ is namespace and fn.__code__ is code and code==expected and fn.__defaults__ is defaults
                    and (defaults is None if count==0 else type(defaults) is tuple and defaults==(None,)*count)
                    and fn.__kwdefaults__ is None and fn.__closure__ is None,'authenticated finder function changed')
        except BootstrapImportRejected:raise
        except BaseException as error:self._fault('finder_authentication',error)
    def authenticate_machinery(self):
        """Called once by the loader outside the audit callback, after dependency import."""
        if self._state[6]:raise ValueError('terminal import authentication cannot restart')
        try:
            self._req(not self._busy and self._state[0]=='ACTIVE','active non-audit finder authentication required')
            self._audit_entry();self._req(self._observed_stage==2 and self._authenticated_stage==0,'complete pending finder transition required')
            authenticated=[]
            for plan,module,namespace,finder,registry,classes,globals_held in self._finder_bindings:
                for spec,cls,functions in classes:
                    for (name,fn),(expected_name,expected,count) in zip(functions,spec[3]):
                        self._req(name==expected_name and fn.__globals__ is namespace and fn.__code__==expected
                            and (fn.__defaults__ is None if count==0 else type(fn.__defaults__) is tuple and fn.__defaults__==(None,)*count)
                            and fn.__kwdefaults__ is None and fn.__closure__ is None,'fixed finder source function differs')
                        authenticated.append((fn,fn.__code__,fn.__defaults__,namespace,expected,count))
                for name,expected,count in plan[8]:
                    fn=namespace[name]
                    self._req(type(fn) is FunctionType and fn.__globals__ is namespace and fn.__code__==expected
                        and (fn.__defaults__ is None if count==0 else type(fn.__defaults__) is tuple and fn.__defaults__==(None,)*count)
                        and fn.__kwdefaults__ is None and fn.__closure__ is None,'fixed finder global function differs')
                    authenticated.append((fn,fn.__code__,fn.__defaults__,namespace,expected,count))
            object.__setattr__(self,'_finder_authenticated',tuple(authenticated));object.__setattr__(self,'_authenticated_stage',2);object.__setattr__(self,'_commit',digest(self._image()))
            self._check_finder_authentication();return self
        except BootstrapImportRejected:raise
        except BaseException as error:self._fault('finder_authentication',error)
    def _audit_entry(self):
        self._req(self._runtime._resource.owner is self._runtime and self._runtime._namespace.module is sys.modules.get(self._policy_profile['allowed_entry_module']['name']),'actual runtime/namespace link changed')
        self._check_cache()
        for name,value,*_ in self._global_bindings:self._req(self._namespace.get(name) is value,'import module binding changed')
        for module,name,value in self._attribute_bindings:self._req(getattr(module,name) is value,'import system binding changed')
        self._ownership()
        self._req(self._creator==(os.getpid(),get_ident()) and self._commit==digest(self._image()),'original import guard required')
        self._observe_machinery()
        return self
    def _entry(self):
        self._audit_entry()
        self._req(self._owner[1].__code__ is self._owner[3],'import callback changed')
        self._req(len(self._profile_raw)==4745 and sha256(self._profile_raw).hexdigest()=='4b731fc38ed2b52bff727acf0b02e4b8da7396cb17f2354225b34348155d9e9c','fixed import policy changed')
        self._check_finder_authentication()
        for name,fn,code,defaults,kw,closure in self._global_bindings:
            self._req(self._namespace.get(name) is fn,'import module binding changed')
            if code is not None:self._req(fn.__code__ is code and fn.__defaults__ is defaults and canonical(fn.__kwdefaults__)==kw and fn.__closure__ is closure,'import helper changed')
        for module,name,value in self._attribute_bindings:self._req(getattr(module,name) is value,'import system binding changed')
        for name,fn,code,defaults,kw,closure in self._own_bindings:
            self._req(getattr(type(self),name) is fn and fn.__code__ is code and fn.__defaults__ is defaults
                and canonical(fn.__kwdefaults__)==kw and fn.__closure__ is closure,'import guard method changed')
        for name,fn,code in self._adapter_bindings:self._req(getattr(self._adapter,name) is fn and fn.__code__ is code,'imported direct adapter binding changed')
        if self._adapter_graph is not None:check_adapter_roots(self._adapter,self._adapter_graph)
        if self._numpy_state is not None:
            module,value=self._numpy_state
            self._req(sys.modules.get('numpy.testing._private.utils') is module and type(module) is ModuleType
                and Path(module.__file__).absolute()==Path(self._numpy_path) and value is False and module._SUPPORTS_SVE is False,
                'NumPy fallback value bookend differs')
        return self
    def _fault(self,reason,original=None):
        error=BootstrapImportRejected('dependency import rejected: '+reason)
        if self._first_error is None:object.__setattr__(self,'_first_error',error if original is None else original)
        object.__setattr__(self,'_state',('FAULTED',self._state[1],self._state[2],self._state[3],self._state[4] + 1,self._state[5],self._state[6],self._state[7] or reason));object.__setattr__(self,'_commit',digest(self._image()))
        raise error
    def _introspect(self,obj,attribute):
        if self._internal is not None:self._fault('introspection_order')
        object.__setattr__(self,'_internal',(obj,attribute))
        result=getattr(obj,attribute)
        if self._internal is not None:self._fault('introspection_missing')
        return result
    def _optional_stack(self):
        marker=tb=frame=None
        try:
            try:raise _SavedImportFrameMarker()
            except _SavedImportFrameMarker as caught:marker=caught;tb=caught.__traceback__
            frame=self._introspect(tb,'tb_frame')
            for _ in range(3):frame=frame.f_back
            numpy_module=sys.modules.get('numpy.testing._private.utils')
            if type(numpy_module) is not ModuleType:return False
            subprocess_module=sys.modules.get('subprocess')
            locations=((1534,subprocess_module),(1026,subprocess_module),(548,subprocess_module),(1247,numpy_module),(1253,numpy_module))
            for expected_code,(line,module) in zip(self._codes,locations):
                if frame is None or self._introspect(frame,'f_code')!=expected_code or frame.f_lineno!=line or frame.f_globals is not vars(module):return False
                frame=frame.f_back
            return True
        finally:
            if marker is not None:marker.__traceback__=None
            object.__setattr__(self,'_internal',None)
            marker=tb=frame=None
    def _audit(self,event,args,token):
        if not self._state[1]:return
        process,process_prefixes,mutations=self._event_sets
        function_mutation=event in ('object.__setattr__','object.__delattr__') and len(args)>=2 and type(args[0]) is FunctionType and type(args[1]) is str and args[1] in ('__code__','__defaults__','__kwdefaults__') and any(
            args[0] is value for binding in self._finder_bindings for value in (
                *(fn for spec,cls,functions in binding[5] for name,fn in functions),*(value for name,value in binding[6])))
        selected=event in process or event.startswith(process_prefixes) or event in mutations or event=='open' or function_mutation
        internal_event=event in ('object.__getattr__','sys._getframe')
        sentinel_event=event=='electricity_grid.saved_import.installation'
        handoff_event=event=='electricity_grid.runtime.audit_handoff_between'
        if not (selected or sentinel_event or handoff_event or self._busy and internal_event):return
        with self._lock:
            if self._creator!=(os.getpid(),get_ident()):self._fault('foreign_thread')
            if self._busy:
                expected=self._internal
                if event=='object.__getattr__' and expected is not None and len(args)==2 and args[0] is expected[0] and args[1]==expected[1]:
                    object.__setattr__(self,'_internal',None);object.__setattr__(self,'_state',(self._state[0],self._state[1],self._state[2],self._state[3],self._state[4],self._state[5] + 1,self._state[6],self._state[7]));object.__setattr__(self,'_commit',digest(self._image()));return
                self._fault('reentrant_event')
            object.__setattr__(self,'_busy',True)
            try:
                self._audit_entry()
                if function_mutation:self._fault('finder_function_mutation')
                if sentinel_event:
                    if self._state[0]!='INSTALLING' or len(args)!=1 or args[0] is not token or self._state[3]!=0:self._fault('installation_sentinel')
                    object.__setattr__(self,'_state',(self._state[0],self._state[1],self._state[2],1,self._state[4],self._state[5],self._state[6],self._state[7]));object.__setattr__(self,'_commit',digest(self._image()));return
                if handoff_event:
                    if not (len(args)==2 and args[0] is self._runtime and args[1] is token and self._handoff_seen==0
                        and self._state[0]=='ACTIVE' and self._state[3]==1 and not self._runtime._resource.guard['active']
                        and self._runtime._resource._early['active']):self._fault('audit_handoff_sentinel')
                    object.__setattr__(self,'_handoff_seen',1);object.__setattr__(self,'_commit',digest(self._image()));return
                if event=='subprocess.Popen':
                    count=self._state[5]
                    if self._state[0]=='ACTIVE' and self._state[2]==0 and tuple(args)==(None,'lscpu',None,None) and self._optional_stack() and self._state[5]-count==6:
                        object.__setattr__(self,'_state',(self._state[0],self._state[1],1,self._state[3],self._state[4],self._state[5],self._state[6],self._state[7]));object.__setattr__(self,'_commit',digest(self._image()));raise _SavedImportCPUQueryDenied('fixed policy denies the NumPy CPU query')
                    self._fault('process_event')
                if event in process or event.startswith(process_prefixes):self._fault('process_event')
                if event in mutations:self._fault('mutation_event')
                if event=='open':
                    path,mode,flags=args[:3]
                    write=type(mode) is str and any(c in mode for c in 'wax+') or type(flags) is int and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
                    if write:self._fault('open_write')
                    if isinstance(path,(str,bytes,os.PathLike)):
                        target=os.path.normcase(os.path.abspath(os.fsdecode(path)))
                        if any(target==p or target.startswith(p+os.sep) for p in self._paths):self._fault('protected_open')
            except (_SavedImportCPUQueryDenied,BootstrapImportRejected):raise
            except BaseException as error:self._fault('classification_error',error)
            finally:object.__setattr__(self,'_busy',False)
    def close(self,primary=None):
        creator,callback,token=self._ownership()
        if creator!=(os.getpid(),get_ident()):raise BootstrapImportUnresolved(self,ValueError('import close owner differs'),())
        with self._lock:
            if self._state[6]:
                if self._failure is not None:raise self._failure
                return
            errors=[]
            try:
                object.__setattr__(self,'_state',(*self._state[:6],True,self._state[7]));object.__setattr__(self,'_commit',digest(self._image()))
                try:self._entry()
                except BaseException as error:errors.append(('bindings',error))
                if not errors:
                    try:_saved_import_inputs(self._profile_raw)
                    except BaseException as error:errors.append(('external_bookend',error))
                if set(sys._current_frames())!={creator[1]}:errors.append(('threads',ValueError('extra Python import thread')))
                if sys.getprofile() is not None or sys.gettrace() is not None:errors.append(('tracing',ValueError('import profile/trace remained active')))
                if self._state[2:5]!=(1,1,0) or self._state[0]!='ACTIVE' or self._numpy_state is None or self._observed_stage!=2 or self._authenticated_stage!=2 or self._handoff_seen!=1:
                    errors.append(('policy_terminal',ValueError('import policy did not complete')))
                if self._first_error is not None and self._first_error is not primary:errors.insert(0,('audit_primary',self._first_error))
            except BaseException as error:errors.append(('close_control',error))
            failed=primary is not None or bool(errors)
            if failed:object.__setattr__(self,'_failure',BootstrapImportUnresolved(self,primary,errors))
            object.__setattr__(self,'_state',('FAULTED' if failed else 'CLOSED',False,*self._state[2:6],True,self._state[7]))
            try:object.__setattr__(self,'_commit',digest(self._image()))
            except BaseException as error:
                object.__setattr__(self,'_state',('FAULTED',False,*self._state[2:6],True,self._state[7]))
                if not failed:
                    object.__setattr__(self,'_failure',BootstrapImportUnresolved(self,primary,(('close_commit',error),)));failed=True
            if failed:raise self._failure from primary
    @property
    def report_raw(self):
        self._ownership()
        return canonical(dict(schema='staged_saved_F_successor_import_boundary_report_v1',authority='DRAFT_NONAUTHORITATIVE',
            phase=self._state[0],optional_Popen_attempts=self._state[2],blocked_optional_attempts=self._state[2],
            audit_handoff_observed=self._handoff_seen,installation_sentinel_observed=self._state[3],violations=self._state[4],internal_introspection_events=self._state[5],
            forced_numpy_SVE_false=self._state[2]==1 and self._numpy_state is not None and self._numpy_state[1] is False,fault_kind=self._state[7],callback_retained=True,hook_installation_observed=self._state[3]==1,hook_active=self._state[1],
            import_boundary_completed=self._state[0]=='CLOSED',source49_bookend_equal=self._source_raw is not None and self._state[0]=='CLOSED',
            machinery_observed_stage=self._observed_stage,machinery_authenticated_stage=self._authenticated_stage,
            machinery_authentication_pending=self._observed_stage!=self._authenticated_stage,
            finder_registry_contents_verified=False,finder_behavior_closure_verified=False,unobserved_RAM_ABA_verified=False,
            finder_function_metadata_bookend_verified=self._authenticated_stage==2 and self._state[0]=='CLOSED',
            finder_function_mutation_guard_installed=self._state[3]==1,baseline_root_authenticated=False,
            source49_expected_truth_bound_by_import_boundary=False,cold_main_self_anchor_verified=False,independent_root_verified=False,
            full_runtime_binding_verified=False,actual_filesystem_alias_verified=False,arbitrary_native_effects_verified=False,
            full_P1_content_verified=False,role_bootstrap=False,permit_issued=False,actual_F=False,run_authority=False,
            scientific_evidence_adopted=False,resource_admission=False,formal_result=False))
    def __reduce__(self):raise TypeError('import guard is local and non-transferable')

