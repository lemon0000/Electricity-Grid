"""Fresh-scope pins for the non-authoritative saved-replay shadow only."""
from dataclasses import fields
import dataclasses
import fractions
from hashlib import sha256
import inspect
import json
from pathlib import Path
import sys
import types

from experiments import staged_rts24_native_probe_v1 as probe
from experiments import staged_rts24_saved_profile_v1 as support
from src import staged_rts24_development_v1 as core,staged_rts24_evidence_store_v1 as codec
from src import staged_rts24_plain_v1 as candidate,staged_rts24_shadow_monitor_v1 as shadow
from src import staged_rts24_journal_v2 as journal,staged_rts24_causal_v2 as policy
from src import staged_rts24_causal_audit_v2 as audit,staged_rts24_child_optimality_v1 as child
from src import staged_rts24_highs_backend_v1 as backend,staged_rts24_numeric_interface_v1 as numeric
from src.staged_rts24_process_guard_v1 import controlled_environment

ROOT=Path(__file__).resolve().parents[1]
APP_NAMES=('experiments experiments.staged_rts24_native_probe_v1 experiments.staged_rts24_saved_profile_v1 '
    'src src.grid src.grid.ac_case src.grid.ac_restoration src.grid.ac_validation src.grid.chronological_dispatch '
    'src.grid.contingency src.grid.dc_opf src.grid.network_grid_need src.grid.rts24 src.grid.rts_gmlc '
    'src.grid.rts_gmlc_scuc src.grid.scopf src.rq2_joint_deliverability_boundary_v1 '
    'src.rq2_joint_deliverability_boundary_v1.debt_cohorts src.rq2_joint_deliverability_boundary_v1.normal_process '
    'src.staged_deliverability_development_v1 src.staged_rts24_audit_v1 src.staged_rts24_causal_audit_v2 '
    'src.staged_rts24_causal_v1 src.staged_rts24_causal_v2 src.staged_rts24_child_optimality_v1 '
    'src.staged_rts24_development_v1 src.staged_rts24_evidence_store_v1 src.staged_rts24_highs_backend_v1 '
    'src.staged_rts24_journal_v2 src.staged_rts24_numeric_interface_v1 src.staged_rts24_plain_v1 '
    'src.staged_rts24_process_guard_v1 src.staged_rts24_reference_queries_v1 '
    'src.staged_rts24_shadow_monitor_v1 src.staged_rts24_shadow_runtime_v1').split()
PACKAGES={'src','experiments','src.grid','src.rq2_joint_deliverability_boundary_v1'}


def require(value,message):
    if not value:raise ValueError(message)


def _code(root,qualname):
    if root.co_qualname==qualname:return root
    for value in root.co_consts:
        if type(value) is types.CodeType:
            result=_code(value,qualname)
            if result is not None:return result


def _constant(value):
    kind=type(value)
    if value is Ellipsis:return ['ellipsis']
    if value is None or kind in (str,int,bool):return [kind.__name__,value]
    if kind is bytes:return ['bytes',value.hex()]
    if kind is float:return ['float',value.hex()]
    if kind is complex:return ['complex',value.real.hex(),value.imag.hex()]
    if kind is types.CodeType:return ['code',_code_tree(value)]
    if kind is tuple:return ['tuple',[_constant(v) for v in value]]
    if kind is frozenset:
        values=[_constant(v) for v in value]
        return ['frozenset',sorted(values,key=lambda v:json.dumps(v,sort_keys=True))]
    raise ValueError('unknown code constant')


def _code_tree(code):
    names=('co_argcount','co_posonlyargcount','co_kwonlyargcount','co_nlocals','co_stacksize','co_flags',
        'co_code','co_consts','co_names','co_varnames','co_filename','co_name','co_qualname',
        'co_firstlineno','co_linetable','co_exceptiontable','co_freevars','co_cellvars')
    return {name:_constant(getattr(code,name)) for name in names}


def _defaults(value):
    if type(value) is dict:return {k:_defaults(v) for k,v in value.items()}
    if type(value) in (tuple,list):return [_defaults(v) for v in value]
    if isinstance(value,type):return dict(type_module=value.__module__,type_name=value.__qualname__)
    if type(value) is fractions.Fraction:return dict(fraction=[value.numerator,value.denominator])
    return _constant(value)


def _namespace(value):
    if type(value) is dict:
        pairs=[[_constant(k),_namespace(v)] for k,v in value.items()]
        return ['dict',sorted(pairs,key=lambda row:json.dumps(row[0],sort_keys=True))]
    return _constant(value)


def routes():
    nested=_code(journal.reopen.__code__,'reopen.<locals>.replay_entry')
    require(nested is not None,'replay entry code missing')
    stages=dict(reopen=journal.reopen,replay_entry=nested,prepare_hour=policy.prepare_hour,
        propose_hour=policy.propose_hour,accept_hour=policy.accept_hour,audit_execution=audit.audit_execution,
        audit_child_lp=child.audit_child_lp,execution_summary=policy.execution_summary)
    forbidden=dict(cas_put=codec.EvidenceStore.put,publication=codec.publish,model=core.build_point_model,
        numeric_compile=numeric.compile_problem,native_model=backend.make_model,native_call=backend.call_highs,
        journal_create=journal.create_session,journal_begin=journal.begin_step,journal_commit=journal.commit_step,
        journal_finish=journal.finish)
    return stages,forbidden


def _application_modules():
    pins={};refs={}
    for name in APP_NAMES:
        module=sys.modules.get(name);spec=getattr(module,'__spec__',None)
        logical=ROOT.joinpath(*name.split('.'))
        path=(logical/'__init__.py') if name in PACKAGES else logical.with_suffix('.py')
        require(type(module) is types.ModuleType and module.__name__==name and spec is not None
            and spec.name==name and Path(spec.origin).resolve()==path
            and Path(module.__file__).resolve()==path,'application module shadow: '+name)
        if '.' in name:
            parent,member=name.rsplit('.',1)
            require(getattr(sys.modules.get(parent),member,None) is module,'application parent binding differs: '+name)
        if name in PACKAGES:
            require(list(module.__path__)==[str(logical)]
                and list(spec.submodule_search_locations)==[str(logical)],'application package path differs: '+name)
        else:require(spec.submodule_search_locations is None,'application module became package: '+name)
        pins[name]=dict(path=str(path),pin=support.stamp(path));refs['application/'+name]=module
    for module in (probe,support,core,codec,candidate,shadow,journal,policy,audit,child,backend,numeric):
        require(sys.modules.get(module.__name__) is module,'captured application module differs')
    return pins,refs


def _function_pin(function,compiled,applications):
    name=function.__module__;module=sys.modules.get(name)
    require(type(module) is types.ModuleType,'function module not already loaded')
    require(name in applications or name.split('.')[0] in sys.stdlib_module_names,'function module outside declared scope')
    if not hasattr(function,'__code__'):
        return dict(module=module.__name__,name=function.__name__,origin=getattr(module,'__file__',None))
    path=Path(module.__file__).resolve()
    require(function.__globals__ is vars(module),'function globals detached from module')
    require(Path(function.__code__.co_filename).resolve()==path,'function code source path differs')
    raw=path.read_bytes()
    if path not in compiled:
        compiled[path]=compile(raw,function.__code__.co_filename,'exec',dont_inherit=True,optimize=sys.flags.optimize)
    expected=_code(compiled[path],function.__code__.co_qualname)
    # marshal encodes reference sharing/interning, so equal code objects can have
    # different marshal bytes. Bind all code fields through a value-only tree.
    actual=_code_tree(function.__code__)
    require(expected is not None and expected==function.__code__ and _code_tree(expected)==actual,'loaded function differs from source')
    return dict(module=module.__name__,name=function.__qualname__,path=str(path),source_sha=sha256(raw).hexdigest(),
        code_sha=sha256(json.dumps(actual,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),
        defaults=_defaults(function.__defaults__),kwdefaults=_defaults(function.__kwdefaults__))


def snapshot():
    require(sys.implementation.name=='cpython' and sys.version_info[:3]==(3,12,12),'exact CPython 3.12.12 required')
    require(Path(sys.executable).resolve()==probe.COMPUTE.resolve()
        and support.stamp(Path(sys.executable))['sha256']==probe.COMPUTE_SHA,'exact compute executable required')
    applications,references=_application_modules()
    require(candidate._legacy_plain is core.plain and child.digest is core.digest,'legacy fallback or direct alias differs')
    require(core.plain.__module__==core.__name__ and core.digest.__module__==core.__name__
        and core.plain.__globals__ is vars(core) and core.digest.__globals__ is vars(core),'legacy function module shadow')
    require(core.asdict is dataclasses.asdict and core.Q is fractions.Fraction and core.json is json,'legacy dependency binding differs')
    require(core.digest.__globals__['plain'] is core.plain and core.digest.__globals__['json'].dumps is json.dumps,'digest binding differs')
    require(_defaults(json.dumps.__kwdefaults__)==_defaults(dict(skipkeys=False,ensure_ascii=True,check_circular=True,allow_nan=True,
        cls=None,indent=None,separators=None,default=None,sort_keys=False)),'JSON default options differ')
    require(_defaults(dataclasses.asdict.__kwdefaults__)==_defaults(dict(dict_factory=dict)),'asdict default factory differs')
    require(candidate.MAX_FAST_DEPTH==64 and len(candidate._KNOWN_FIELDS)==len(codec.CLASSES)==20,'candidate registry scope differs')
    classes=[]
    for cls,names in candidate._KNOWN_FIELDS:
        module=sys.modules[cls.__module__];path=Path(module.__file__).resolve()
        require(codec.CLASSES.get(cls.__name__) is cls and getattr(module,cls.__name__) is cls
            and tuple(f.name for f in fields(cls))==names,'registered class/fields differ')
        require(type(cls) is type and cls.__getattribute__ is object.__getattribute__,'custom registered field access')
        require(all(inspect.getattr_static(type(inspect.getattr_static(cls,name,None)),'__get__',None) is None
            for name in names),'registered field descriptor')
        require(path==ROOT.joinpath(*cls.__module__.split('.')).with_suffix('.py'),'class module shadow')
        classes.append(dict(module=cls.__module__,name=cls.__qualname__,fields=list(names),path=str(path),pin=support.stamp(path)))
        references['class/'+cls.__name__]=cls;references['module/'+cls.__module__]=module
    stages,forbidden=routes()
    functions=dict(legacy_plain=core.plain,legacy_digest=core.digest,legacy_asdict=core.asdict,
        candidate_walk=candidate._walk,candidate_plain=candidate.plain,candidate_bytes=candidate.canonical_bytes,
        json_dumps=json.dumps,dataclass_fields=dataclasses.fields,fraction_str=fractions.Fraction.__str__,
        json_encode=json.JSONEncoder.encode,json_iterencode=json.JSONEncoder.iterencode,
        monitor_enter=shadow.ShadowMonitor.__enter__,monitor_start=shadow.ShadowMonitor._start,
        monitor_return=shadow.ShadowMonitor._returned,monitor_exit=shadow.ShadowMonitor.__exit__)
    functions.update({'stage/'+k:v for k,v in stages.items() if callable(v)})
    functions.update({'forbidden/'+k:v for k,v in forbidden.items()})
    functions.update({'monitor/'+k:v for k,v in vars(shadow.ShadowMonitor).items() if type(v) is types.FunctionType})
    compiled={};function_pins={}
    for name,function in functions.items():
        function_pins[name]=_function_pin(function,compiled,applications)
        references['function/'+name]=function;references['code/'+name]=function.__code__
    api={}
    for name in ('use_tool_id','free_tool_id','get_tool','set_events','get_events','set_local_events','get_local_events','register_callback'):
        function=getattr(sys.monitoring,name)
        require(type(function) is types.BuiltinFunctionType,'monitoring API replaced: '+name)
        api[name]=dict(name=function.__name__,module=function.__module__)
        references['monitoring/'+name]=function
    stdlib={};compute=Path(sys.prefix).resolve()
    for name,module in sorted(tuple(sys.modules.items())):
        if name.split('.')[0] not in sys.stdlib_module_names or not isinstance(module,types.ModuleType):continue
        spec=getattr(module,'__spec__',None);origin=getattr(spec,'origin',None);declared=getattr(spec,'name',None)
        path=getattr(module,'__file__',None)
        record=dict(module_name=module.__name__,spec_name=declared,origin=origin,path=path)
        if path is not None:
            source=Path(path).resolve();require(source.is_relative_to(compute),'stdlib module shadow: '+name)
            if origin not in ('built-in','frozen'):
                require(type(declared) is str and declared,'stdlib import name missing')
                logical=compute/'Lib'/Path(*declared.split('.'))
                allowed={logical.with_suffix('.py').resolve(),(logical/'__init__.py').resolve(),
                    (compute/'DLLs'/(declared+'.pyd')).resolve()}
                require(source in allowed,'noncanonical stdlib module path: '+name)
            record.update(resolved=str(source),pin=support.stamp(source))
        elif origin not in ('built-in','frozen'):
            # CPython's pyexpat creates two data-only module namespaces without
            # a file or ModuleSpec. Bind their exact owner and typed contents.
            require(name in ('pyexpat.errors','pyexpat.model'),'unknown stdlib origin: '+name)
            owner=sys.modules.get('pyexpat');member=name.split('.')[1]
            require(owner is not None and getattr(owner,member,None) is module,'synthetic stdlib owner differs')
            record.update(owner='pyexpat',namespace=_namespace(vars(module)))
        stdlib[name]=record;references['stdlib/'+name]=module
    for name in ('dataclasses','fractions','json','json.encoder','json.decoder','json.scanner','copy','hashlib','_hashlib','_json'):
        require(name in stdlib,'critical stdlib module not loaded: '+name)
    pins=dict(python=sys.version,executable=str(Path(sys.executable).resolve()),executable_pin=support.stamp(Path(sys.executable)),
        controlled_environment_sha=core.digest(controlled_environment()),application_modules=applications,classes=classes,functions=function_pins,
        flags=dict(no_user_site=sys.flags.no_user_site,dont_write_bytecode=sys.dont_write_bytecode),
        stdlib=stdlib,monitoring_api=api,json_options=dict(sort_keys=True,separators=[',',':'],allow_nan=False,ensure_ascii=True,encoding='utf-8'),
        scope='loaded_stdlib_and_original_selected_application_pins_not_full_third_party_or_resolved_OS_closure')
    return pins,references


def unchanged(before,refs):
    after,current=snapshot()
    require(after==before and set(current)==set(refs)
        and all(current[k] is value for k,value in refs.items()),'shadow runtime identity changed')
    return after
