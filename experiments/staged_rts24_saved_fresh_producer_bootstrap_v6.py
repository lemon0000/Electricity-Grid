"""Deferred creating-bootstrap bundle; the fixed public issuer stays disabled.

Import return finalizes construction. A prepared, profile-matched LIVE owner
may request bundle finalization inside the coordinator cleanup boundary.
"""
import ast
import builtins
from hashlib import sha256
from importlib import _bootstrap, machinery
import json
import os
from pathlib import Path
import sys
from threading import get_ident
from types import CodeType,FunctionType,ModuleType

ROOT=Path(__file__).absolute().parents[1]
ENTRY='experiments/staged_rts24_saved_fresh_adoption_v1.py'
ADAPTER='src/staged_rts24_saved_fresh_adoption_v1.py'
SOURCE_EPOCH='acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'
_RUNTIME_TYPE=globals().get('_RUNTIME_TYPE')
_P1_PERMISSION_PROGRAM=globals().get('_P1_PERMISSION_PROGRAM')
_P1_PERMISSION_RAW=globals().get('_P1_PERMISSION_RAW')
_BUILTIN_NAMESPACE=vars(builtins)
_GUARD=globals().get('_GUARD')
LIFECYCLE_PIN=(40820,'51682c35d4432633f143c7c53b78106e157eb17ef184adff6ebb30b73236b6a1')
LIFECYCLE_SUCCESSOR_PIN=(64991, 'f4071ab40444af9d6a45accc92770454139ff2b106db37be84de20185735c7c5')
FALSE_FIELDS=('initial_project_state_authenticated','independent_tcb_authenticated','producer_capability_verified',
    'full_runtime_binding_verified','full_P1_content_verified','role_bootstrap','permit_issued','run_authority',
    'resource_admission','scientific_evidence_adopted','formal_result','actual_F','unobserved_RAM_ABA_verified')
_ABSENT=object()


def require(value,message):
    if not value:raise ValueError(message)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return len(raw),sha256(raw).hexdigest()
def creator():return os.getpid(),get_ident()


def check_program():
    require(type(_GUARD) is tuple and len(_GUARD)==3,'bootstrap-held source program required')
    FunctionType(_GUARD[0],_GUARD[1])(*_GUARD[2])


def function_spec(function):
    require(type(function) is FunctionType,'original Python callable required')
    closure=function.__closure__
    cells=() if closure is None else tuple(cell.cell_contents for cell in closure)
    return function,function.__code__,function.__globals__,function.__defaults__,function.__kwdefaults__,closure,cells


def verify_function(spec):
    function,code,namespace,defaults,kw,closure,cells=spec
    require(function.__code__ is code and function.__globals__ is namespace and function.__defaults__ is defaults
        and function.__kwdefaults__ is kw and function.__closure__ is closure
        and (closure is None or all(cell.cell_contents is held for cell,held in zip(closure,cells))),
        'original loader callable changed')


def loader_roots():
    return tuple(function_spec(function) for function in (machinery.SourceFileLoader.exec_module,
        machinery.SourceFileLoader.get_code,machinery.SourceFileLoader.get_filename,_bootstrap._call_with_frames_removed))


def check_loader_roots(plan):
    require(machinery.SourceFileLoader is plan._loader_type and builtins.exec is plan._exec
        and sys._getframe is plan._getframe,'original execution primitives changed')
    current=(machinery.SourceFileLoader.exec_module,machinery.SourceFileLoader.get_code,
        machinery.SourceFileLoader.get_filename,_bootstrap._call_with_frames_removed)
    for function,spec in zip(current,plan._loader_roots):
        require(function is spec[0],'original loader dispatch changed');verify_function(spec)


def metadata(module,name,relative,root,*,initial):
    require(type(module) is ModuleType and vars(module).get('__name__')==name,'exact named source module required')
    namespace=vars(module);path=str(root/relative);spec=namespace.get('__spec__');loader=namespace.get('__loader__')
    require(namespace.get('__file__')==path and namespace.get('__builtins__',_BUILTIN_NAMESPACE) is _BUILTIN_NAMESPACE,'source file/builtins identity differs')
    require(type(loader) is machinery.SourceFileLoader and loader.name==name and loader.path==path,
        'exact standard source loader required')
    require(spec is not None and type(spec) is machinery.ModuleSpec and spec.name==name and spec.origin==path
        and spec.loader is loader,'original source spec required')
    package=name if relative.endswith('/__init__.py') else name.rpartition('.')[0]
    require(namespace.get('__package__')==package,'source package differs')
    if initial:
        allowed={'__name__','__doc__','__package__','__loader__','__spec__','__file__','__cached__','__builtins__'}
        if relative.endswith('/__init__.py'):allowed.add('__path__')
        require(set(namespace)<=allowed and namespace.get('__doc__') is None,'source namespace was prepopulated')
        require(spec._initializing is True,'source loader initialization required')
    else:require(spec._initializing is False,'source import did not return')
    return spec,loader,package


class ProjectConstruction:
    __slots__=('_owner','_creator','_root','_registry','_sources','_units','_entry_name','_adapter_name','_entry_proof',
        '_rows','_phase','_failure','_loader_roots','_loader_type','_exec','_getframe','_observed','_seal')
    def __new__(cls,*args,**kwargs):raise TypeError('use the creating bootstrap')
    def __setattr__(self,name,value):raise AttributeError('construction fields are frozen')
    def __delattr__(self,name):raise AttributeError('construction fields are frozen')
    def __reduce__(self):raise TypeError('construction evidence is process-local')


def image(plan):
    return (id(plan._owner),plan._creator,str(plan._root),id(plan._registry),plan._entry_name,plan._adapter_name,
        tuple((name,relative,id(raw),pin(raw),id(plan._units[name])) for name,(relative,raw) in sorted(plan._sources.items())),
        tuple((name,tuple(id(value) for value in row)) for name,row in sorted(plan._rows.items())),
        tuple(id(value) for value in plan._entry_proof),plan._phase,id(plan._failure),plan._observed,
        tuple(tuple(id(value) for value in spec) for spec in plan._loader_roots))


def commit(plan,**changes):
    for name,value in changes.items():object.__setattr__(plan,name,value)
    object.__setattr__(plan,'_seal',pin(canonical(image(plan))))


def check_entry_proof(plan):
    owner,namespace,module,raw,unit=plan._entry_proof
    require(owner is plan._owner and owner._namespace is namespace and namespace.module is module
        and namespace._raw is raw and namespace._unit is unit and namespace._exec_attempts==namespace._exec_completed==2
        and namespace._actual_initialized is True,'original paired ENTRY construction proof required')
    require(plan._registry.get(plan._entry_name) is module and vars(module).get('__file__')==str(plan._root/plan._sources[plan._entry_name][0])
        and raw is plan._sources[plan._entry_name][1] and unit==plan._units[plan._entry_name],
        'ENTRY held raw/code/module differs')


def check(plan,*,final=False,owner_bookend=True):
    check_program()
    require(type(plan) is ProjectConstruction and plan._creator==creator(),'creating construction thread required')
    if plan._failure is not None:raise plan._failure
    require(plan._seal==pin(canonical(image(plan))) and plan._registry is sys.modules,'construction state/registry differs')
    require(plan._phase in (('FINAL','BUNDLED') if final else ('COLLECTING',)),'construction phase differs')
    check_loader_roots(plan);check_entry_proof(plan)
    phases=('IMPORTING','OBSERVED','LIVE') if final else ('IMPORTING',)
    require(plan._owner._creator[:2]==plan._creator and plan._owner._phase in phases,
        'same active creating runtime required')
    if owner_bookend:require(plan._owner.entry() is plan._owner,'same creating runtime required')
    if final:
        require(set(plan._rows)==set(plan._sources)-{plan._entry_name},'complete final construction rows required')
        for name,row in plan._rows.items():
            module,spec,loader,code,package=row
            require(plan._registry.get(name) is module
                and metadata(module,name,plan._sources[name][0],plan._root,initial=False)==(spec,loader,package)
                and code==plan._units[name],'final construction row changed')
    return plan


def reject(plan,error):
    if plan._failure is not None:raise plan._failure
    commit(plan,_phase='FAILED',_failure=error)
    raise error


def _begin(owner,sources,root,entry_name,adapter_name):
    """Private generic constructor for ordinary synthetic fixtures."""
    require(type(sources) is dict and 1<len(sources)<=37 and entry_name in sources and adapter_name in sources,
        'closed source selection required')
    require(root.is_absolute() and all(type(name) is str and type(pair) is tuple and len(pair)==2
        and type(pair[0]) is str and type(pair[1]) is bytes and not Path(pair[0]).is_absolute()
        and '..' not in Path(pair[0]).parts for name,pair in sources.items()),'ordinary held source pairs required')
    require(len({str(root/pair[0]).casefold() for pair in sources.values()})==len(sources)
        and sum(len(pair[1]) for pair in sources.values())<=2097152,'closed bounded source paths required')
    require(owner.entry() is owner and owner._creator[:2]==creator(),'creating runtime required')
    require(all(name==entry_name or name not in sys.modules for name in sources),'project dependencies must be cold')
    namespace=owner._namespace;entry_module=namespace.module;raw=sources[entry_name][1]
    plan=object.__new__(ProjectConstruction)
    values=dict(_owner=owner,_creator=creator(),_root=root,_registry=sys.modules,_sources=dict(sources),
        _units={name:compile(raw,str(root/relative),'exec',dont_inherit=True,optimize=0) for name,(relative,raw) in sources.items()},
        _entry_name=entry_name,_adapter_name=adapter_name,_entry_proof=(owner,namespace,entry_module,raw,namespace._unit),
        _rows={},_phase='COLLECTING',_failure=None,_loader_roots=loader_roots(),_loader_type=machinery.SourceFileLoader,
        _exec=builtins.exec,_getframe=sys._getframe,_observed=0)
    for name,value in values.items():object.__setattr__(plan,name,value)
    commit(plan);check(plan);return plan


def begin_project_construction(owner):
    require(_RUNTIME_TYPE is not None and type(owner) is _RUNTIME_TYPE,'bootstrap-held exact runtime type required')
    require(owner._phase=='IMPORTING' and owner._adapter is None and owner._consume_state is None,
        'construction must precede adapter import/consumer reservation')
    raw_map=dict(owner._sources);require(len(raw_map)==len(owner._sources)==49,'complete held Source49 required')
    pins={name:dict(bytes=len(raw),sha256=sha256(raw).hexdigest()) for name,raw in raw_map.items()}
    require(pin(canonical(pins))[1]==SOURCE_EPOCH,'fixed Source49 epoch required')
    sources={name[:-3].replace('/','.').removesuffix('.__init__'):(name,raw) for name,raw in raw_map.items()
        if name.startswith('src/') and name.endswith('.py') or name==ENTRY}
    require(len(sources)==37,'complete selected project set required')
    return _begin(owner,sources,ROOT,ENTRY[:-3].replace('/','.'),ADAPTER[:-3].replace('/','.'))


def observe_exec(plan,event,args):
    """Called from the existing boundary hook before its busy transaction."""
    if event!='exec':return
    if not args or type(args[0]) is not CodeType:return
    code=args[0]
    names=[name for name,(relative,_) in plan._sources.items() if code.co_filename==str(plan._root/relative)]
    if not names:return
    frame=call_frame=loader_frame=None
    try:
        check(plan,owner_bookend=False)
        require(len(names)==1,'unique source code path required');name=names[0]
        require(name!=plan._entry_name and name not in plan._rows,'duplicate/reloaded project execution')
        require(code.co_name=='<module>' and code==plan._units[name],'executed code differs from held source unit')
        module=plan._registry.get(name);relative,_=plan._sources[name]
        spec,loader,package=metadata(module,name,relative,plan._root,initial=True)
        # An exec audit event alone has no globals argument. Bind it to the
        # authenticated CPython loader/call frames and their actual arguments.
        frame=plan._getframe(1)
        for _ in range(10):
            if frame is None:break
            if frame.f_code is plan._loader_roots[3][1]:
                call_frame=frame;loader_frame=frame.f_back;break
            frame=frame.f_back
        require(call_frame is not None and loader_frame is not None
            and call_frame.f_globals is plan._loader_roots[3][2]
            and loader_frame.f_code is plan._loader_roots[0][1]
            and loader_frame.f_globals is plan._loader_roots[0][2],'original loader execution frames required')
        call=call_frame.f_locals;loaded=loader_frame.f_locals
        require(call.get('f') is plan._exec and type(call.get('args')) is tuple
            and len(call['args'])==2 and call['args'][0] is code and call['args'][1] is vars(module)
            and call.get('kwds')=={} and loaded.get('self') is loader and loaded.get('module') is module
            and loaded.get('code') is code,'exec globals are not the registered module namespace')
        plan._rows[name]=(module,spec,loader,code,package)
        commit(plan,_observed=plan._observed+1)
    except BaseException as error:reject(plan,error)
    finally:frame=call_frame=loader_frame=None


def finalize_project_construction(plan,adapter):
    try:
        check(plan)
        require(plan._registry.get(plan._adapter_name) is adapter and type(adapter) is ModuleType,'original returned adapter required')
        require(set(plan._rows)==set(plan._sources)-{plan._entry_name} and plan._observed==len(plan._sources)-1,
            'complete once-only source execution set required')
        for name,row in plan._rows.items():
            module,spec,loader,code,package=row;relative,_=plan._sources[name]
            require(plan._registry.get(name) is module and metadata(module,name,relative,plan._root,initial=False)==(spec,loader,package)
                and code==plan._units[name],'source import return identity differs')
        modules={name:(plan._entry_proof[2] if name==plan._entry_name else plan._rows[name][0]) for name in plan._sources}
        for name,module in tuple(plan._registry.items()):
            if type(module) is not ModuleType:continue
            path=vars(module).get('__file__')
            selected=name in modules
            under=type(path) is str and Path(path).is_absolute() and Path(path).is_relative_to(plan._root)
            if selected or under:require(selected and modules[name] is module,'extra project module/alias retained')
        commit(plan,_phase='FINAL');return check(plan,final=True)
    except BaseException as error:reject(plan,error)


def selected_modules(plan):
    check(plan,final=True)
    return {name:(plan._entry_proof[2] if name==plan._entry_name else plan._rows[name][0]) for name in plan._sources}


def make_project_bootstrap_bundle(plan,graph,graph_raw,lifecycle,lifecycle_raw,capture_code,admission):
    try:return _make_bundle(plan,graph,graph_raw,lifecycle,lifecycle_raw,capture_code,admission)
    except BaseException as error:reject(plan,error)


def _make_bundle(plan,graph,graph_raw,lifecycle,lifecycle_raw,capture_code,admission):
    """Deferred fixed-issuer request; no producer slot or P1 content call."""
    check(plan,final=True)
    require(plan._phase=='FINAL','single bundle issuance required')
    require(admission is None and type(capture_code) is CodeType,'no caller P1 admission accepted')
    owner=plan._owner
    require(owner._phase=='LIVE' and owner._import_profile_matched is True and owner._consume_state=='PREPARED'
        and owner._consumer_plan is not None,'prepared profile-matched LIVE owner required')
    require(owner._resource.owner is owner and owner._resource.phase=='LIVE','same live resource owner required')
    require(pin(lifecycle_raw)==LIFECYCLE_SUCCESSOR_PIN,'exact lifecycle abort successor source required')
    require(type(graph) is ModuleType and type(lifecycle) is ModuleType,'held helper modules required')
    utilities=lifecycle_utilities((ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v1.py').read_bytes())
    # Authenticate source-owned graph definitions before any capture call.
    witness=utilities['_program_witness'](vars(graph),graph_raw)
    lifecycle_witness=utilities['_program_witness'](vars(lifecycle),lifecycle_raw)
    guard=utilities['_verify_programs'].__code__,dict(__builtins__=dict(vars(builtins)),FunctionType=FunctionType),((witness,lifecycle_witness),utilities['_metadata'].__code__)
    FunctionType(guard[0],guard[1])(*guard[2])
    modules=selected_modules(plan)
    snapshot=graph.capture(modules,dict(plan._sources),plan._root,registry=plan._registry)
    require(graph.check(snapshot)['structure_and_identity_stable'] is True,'returned project graph differs')
    verify_bundle(plan,graph,snapshot,guard)
    # No callback, local token, bool or profile data is an external root. The
    # pinned public program below always rejects issue. Future activation must
    # use a separately authorized source successor and a new observation schema.
    admission=permission_operation('issue',(owner,owner._consumer_plan,snapshot,owner._boundary))
    require(admission is not None,'genuine outer-issued diagnostic admission required')
    inject=dict(_RUNTIME_TYPE=type(plan._owner),_ADMITTED_OWNER=plan._owner,_P1_AUTHORITY=admission,
        _CAPTURE_CODE=capture_code,_GRAPH_MODULE=graph,_PROJECT_SNAPSHOT=snapshot,
        _P1_PERMISSION_PROGRAM=_P1_PERMISSION_PROGRAM,_P1_PERMISSION_RAW=_P1_PERMISSION_RAW)
    lifecycle_private=utilities['_private_functions'](vars(lifecycle))
    dispatch=lifecycle_private['source_dispatch'](lifecycle_raw,inject,graph_raw)
    # No snapshot-only dispatcher escapes: the creating bootstrap retains this
    # outer CodeType/state and invokes it on every lifecycle operation.
    state=(plan,graph,snapshot,dispatch,verify_bundle.__code__,globals(),guard)
    commit(plan,_phase='BUNDLED')
    return bundle_dispatch.__code__,dict(__builtins__=dict(vars(builtins)),FunctionType=FunctionType),state


def verify_bundle(plan,graph,snapshot,guard):
    FunctionType(guard[0],guard[1])(*guard[2])
    modules=selected_modules(plan)
    require(type(snapshot) is graph.ProducerProjectSnapshot and snapshot._registry is plan._registry
        and dict(snapshot._modules)==modules and dict(snapshot._sources)==plan._sources,
        'construction/snapshot source-module bindings differ')
    require(all(dict(snapshot._sources)[name][1] is raw for name,(_,raw) in plan._sources.items()),
        'snapshot must retain the original held raw objects')
    require(graph.check(snapshot)['structure_and_identity_stable'] is True,'construction graph continuity differs')
    return True


def bundle_dispatch(state,producer,operation,args,kwargs):
    plan,graph,snapshot,dispatch,verify_code,context,guard=state
    if producer is not None:
        inner=dispatch[2][0]
        if type(producer) is not inner['RetainedProducer'] or producer._creator!=(context['os'].getpid(),context['get_ident']()):
            raise ValueError('creating exact bundle producer required')
        if producer._failure is not None or producer._phase=='CLOSED':
            return FunctionType(dispatch[0],dispatch[1])(dispatch[2],producer,operation,args,kwargs)
    try:FunctionType(verify_code,context)(plan,graph,snapshot,guard)
    except BaseException as error:
        if producer is not None:
            return FunctionType(dispatch[0],dispatch[1])(dispatch[2],producer,'bootstrap_abort',(error,),{})
        raise
    return FunctionType(dispatch[0],dispatch[1])(dispatch[2],producer,operation,args,kwargs)


def lifecycle_utilities(raw):
    require(pin(raw)==LIFECYCLE_PIN,'fixed private lifecycle utilities required')
    path=str(ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v1.py')
    namespace=dict(__file__=path,__name__='_construction_held_lifecycle_utilities')
    exec(compile(raw,path,'exec',dont_inherit=True,optimize=0),namespace,namespace)
    return namespace


def program_dispatch(state,operation,args,kwargs):
    context,operations=state
    if operation not in operations:raise ValueError('fixed source construction operation required')
    code,defaults,kw=operations[operation]
    function=FunctionType(code,context,'held_construction_'+operation,defaults);function.__kwdefaults__=kw
    return function(*args,**kwargs)


def source_program(raw,extra,lifecycle_raw):
    """Creating-bootstrap held entry; authenticates no user run authority."""
    require(type(raw) is bytes and type(extra) is dict,'source bytes and bootstrap bindings required')
    utilities=lifecycle_utilities(lifecycle_raw)
    namespace=dict(__file__=__file__,__name__='_construction_private_source',**extra)
    exec(compile(raw,__file__,'exec',dont_inherit=True,optimize=0),namespace,namespace)
    witness=utilities['_program_witness'](namespace,raw)
    isolated=dict(__builtins__=dict(vars(builtins)),FunctionType=FunctionType)
    guard=utilities['_verify_programs'].__code__,isolated,((witness,),utilities['_metadata'].__code__)
    context=utilities['_private_functions'](namespace);context['_GUARD']=guard
    names=('_begin','begin_project_construction','observe_exec','finalize_project_construction',
        'make_project_bootstrap_bundle','selected_modules','check','new_import_bridge')
    operations={name:(context[name].__code__,context[name].__defaults__,context[name].__kwdefaults__) for name in names}
    return context['program_dispatch'].__code__,isolated,(context,operations)


def new_import_bridge(owner,graph,graph_raw,lifecycle,lifecycle_raw,capture_code,admission):
    """Prepare before B_S binding capture; no import, producer claim or P1."""
    check_program()
    require(admission is None,'external P1 issuer is unavailable; local tokens are rejected')
    require(_RUNTIME_TYPE is not None and type(owner) is _RUNTIME_TYPE and owner._phase=='ADOPTED',
        'creating pre-import runtime required')
    require(owner.entry() is owner and owner._creator[:2]==creator(),'original creating pre-import owner required')
    state=dict(owner=owner,creator=creator(),phase='PREPARED',plan=None,bundle=None,failure=None,
        graph=graph,graph_raw=graph_raw,lifecycle=lifecycle,lifecycle_raw=lifecycle_raw,
        capture_code=capture_code,admission=admission)
    state['seal']=pin(canonical(bridge_image(state)))
    return import_bridge_dispatch.__code__,dict(__builtins__=dict(vars(builtins)),FunctionType=FunctionType),(
        state,import_bridge_event.__code__,globals())


def bridge_image(state):
    return (id(state['owner']),state['creator'],state['phase'],id(state['plan']),id(state['bundle']),id(state['failure']),
        tuple(id(state[name]) for name in ('graph','graph_raw','lifecycle','lifecycle_raw','capture_code','admission')))


def import_bridge_dispatch(held,stage,runtime,args):
    state,code,context=held
    return FunctionType(code,context)(state,stage,runtime,args)


def import_bridge_event(state,stage,runtime,args):
    check_program()
    require(state['creator']==creator() and runtime is state['owner'],'creating bridge runtime required')
    if state['failure'] is not None:raise state['failure']
    require(state['seal']==pin(canonical(bridge_image(state))),'import bridge state differs')
    try:
        if stage=='before_import':
            require(state['phase']=='PREPARED' and not args,'single construction import required')
            state['plan']=begin_project_construction(runtime);state['phase']='COLLECTING'
        elif stage=='exec':
            if state['phase']=='PREPARED':return None
            observe_exec(state['plan'],'exec',args)
        elif stage=='after_import':
            require(state['phase']=='COLLECTING' and type(args) is tuple and len(args)==1,'single import return required')
            plan=finalize_project_construction(state['plan'],args[0])
            state['phase']='READY'
        elif stage=='bundle':
            require(state['phase']=='READY' and not args,'single deferred bundle finalization required')
            state['bundle']=make_project_bootstrap_bundle(state['plan'],state['graph'],state['graph_raw'],
                state['lifecycle'],state['lifecycle_raw'],state['capture_code'],None)
            state['phase']='BUNDLED';state['seal']=pin(canonical(bridge_image(state)))
            return state['bundle']
        elif stage=='report':
            require(state['phase']=='READY' and not args,'finalized pre-admission construction required')
            plan=check(state['plan'],final=True)
            result=dict(schema='staged_saved_F_pre_admission_construction_v1',authority='DRAFT_NONAUTHORITATIVE',
                source_modules=len(plan._sources),loader_execs=plan._observed,
                entry_execs=plan._entry_proof[1]._exec_completed,bundle_phase=state['phase'],
                P1_reads=0,admission_present=False,**{name:False for name in FALSE_FIELDS})
            require(len(canonical(result))<=32768,'bounded pre-admission construction report required')
            return result
        elif stage=='release':
            require(state['phase']=='BUNDLED' and not args and runtime._phase=='CLOSED'
                and runtime._consume_state=='CONSUMED' and runtime._resource.phase=='CLOSED'
                and not any(runtime._resource.pending),'closed successful producer required before release')
            held=_P1_PERMISSION_PROGRAM
            require(held[2][2].guard_phase=='CLOSED' and held[2][2].phase=='RETIRED','closed permission required before release')
            for key in ('owner','plan','bundle','graph','graph_raw','lifecycle','lifecycle_raw','capture_code','admission'):
                state[key]=None
            state['phase']='RELEASED'
        else:raise ValueError('unknown fixed import bridge stage')
        state['seal']=pin(canonical(bridge_image(state)))
        return None
    except BaseException as error:
        state['failure']=error;state['phase']='FAILED';state['seal']=pin(canonical(bridge_image(state)))
        raise


def current():
    """Compile-only source obligations; no audit installation or project exec."""
    path=ROOT/'results/tables/staged_rts24_saved_fresh_producer_project_graph_v1_non_authoritative/registration.json'
    contract=json.loads(path.read_bytes())['graph_contract']['source_contract']
    source=contract['source_pins'];require(pin(canonical(source))[1]==SOURCE_EPOCH,'fixed Source49 contract required')
    counts=dict(modules=0,functions=0,classes=0);module_sources={}
    for relative,want in source.items():
        raw=(ROOT/relative).read_bytes();require(pin(raw)==(want['bytes'],want['sha256']),'frozen source differs')
        if not (relative.startswith('src/') and relative.endswith('.py') or relative==ENTRY):continue
        tree=ast.parse(raw);compile(raw,str(ROOT/relative),'exec',dont_inherit=True,optimize=0)
        counts['modules']+=1;counts['functions']+=sum(type(node) is ast.FunctionDef for node in tree.body)
        counts['classes']+=sum(type(node) is ast.ClassDef for node in tree.body)
        module_sources[relative[:-3].replace('/','.').removesuffix('.__init__')]=relative
    require(counts==dict(modules=37,functions=500,classes=146),'fixed source declaration census differs')
    return None,dict(schema='staged_saved_F_project_bootstrap_contract_v3',authority='DRAFT_NONAUTHORITATIVE',
        source_epoch=SOURCE_EPOCH,source_contract=contract,module_sources=module_sources,declarations=counts,
        operation='deferred_bundle_with_disabled_public_issue',P1_issuer_implemented=False,P1_reads=0,source49_target_modules_executed=0,
        **{name:False for name in FALSE_FIELDS})



P1_PERMISSION_PIN=(18952,'0fa4420f1fb3ccfd70f234d7276de79bd780ce796b708ea58c912ebb9a74f9c7')


def permission_operation(operation,args):
    """Exact fixed permission dispatcher; no injected authorization callback."""
    require(operation=='issue' and type(args) is tuple,'closed deferred permission operation required')
    require(type(_P1_PERMISSION_RAW) is bytes and pin(_P1_PERMISSION_RAW)==P1_PERMISSION_PIN,'fixed permission source required')
    spec=_P1_PERMISSION_PROGRAM
    require(type(spec) is tuple and len(spec)==3 and type(spec[0]) is CodeType and type(spec[1]) is dict
        and type(spec[2]) is tuple and len(spec[2])==3,'held permission program required')
    unit=compile(_P1_PERMISSION_RAW,str(ROOT/'experiments/staged_rts24_saved_fresh_p1_permission_v1.py'),
        'exec',dont_inherit=True,optimize=0)
    codes=[code for code in unit.co_consts if type(code) is CodeType and code.co_name==code.co_qualname=='program_dispatch']
    require(len(codes)==1 and spec[0]==codes[0] and set(spec[1])=={'__builtins__','FunctionType'}
        and spec[1]['FunctionType'] is FunctionType,'fixed permission dispatch code required')
    native=spec[1]['__builtins__'];expected=vars(builtins)
    require(type(native) is dict and set(native)==set(expected) and all(native[key] is value for key,value in expected.items()),
        'native permission interpreter required')
    return FunctionType(spec[0],spec[1])(spec[2],operation,args)
