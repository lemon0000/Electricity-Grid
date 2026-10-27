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

_CENSUS_IO=_CENSUS_IO
_CENSUS_DUMPS=_CENSUS_IO[3]
_CENSUS_NATIVE=(len,type,max,tuple,ValueError,OSError,dict,list)
_CENSUS_PHASES=('identity1','runtime_link','cache','globals_attrs','ownership','image_digest','machinery')
_CENSUS=dict(active=False,ever_started=False,boundary=None,start=None,end=None,entered=0,passed=0,rejected=0,observed=0,
    stamp=0,seen_stamp=0,last_passed=False,inflight=False,phase=None,last_incomplete=None,seq=0,bytes=0,
    errors=[],clock_broken=False,token=object(),installed=0,reason=None,cache_ref=sys.path_importer_cache,cache_base=0,stage=0,
    buckets={name:[0,0.0,0.0] for name in (*_CENSUS_PHASES,'entry_total','audit_body_inclusive')})

class AuditCensusStop(BaseException):pass

def _census_error(error, _state=_CENSUS, _io=_CENSUS_IO, _native=_CENSUS_NATIVE, _base=BaseException, _group=BaseExceptionGroup, _stop=AuditCensusStop):
    _native_0 = _native[0]
    try:
        if _native_0(_state['errors']) < 4:
            _state['errors'].append(error)
        _state['clock_broken'] = True
    except _base:
        pass

def _census_clock(_state=_CENSUS, _io=_CENSUS_IO, _native=_CENSUS_NATIVE, _base=BaseException, _group=BaseExceptionGroup, _stop=AuditCensusStop, _dep_error=_census_error):
    _native_1 = _native[1]
    _native_4 = _native[4]
    if _state['clock_broken']:
        return None
    try:
        value = _io[0]()
        if _native_1(value) is not float or not 0 <= value <= 1000000000000.0:
            raise _native_4('invalid census clock')
        return value
    except _base as error:
        _dep_error(error)
        return None

def _census_record(name, start, end, _state=_CENSUS, _io=_CENSUS_IO, _native=_CENSUS_NATIVE, _base=BaseException, _group=BaseExceptionGroup, _stop=AuditCensusStop, _dep_error=_census_error):
    _native_2 = _native[2]
    _native_4 = _native[4]
    if start is None or end is None:
        return
    try:
        elapsed = end - start
        if not 0 <= elapsed <= 8:
            raise _native_4('invalid census elapsed time')
        row = _state['buckets'][name]
        row[0] += 1
        row[1] += elapsed
        row[2] = _native_2(row[2], elapsed)
    except _base as error:
        _dep_error(error)

def _census_cut(name, start, _state=_CENSUS, _io=_CENSUS_IO, _native=_CENSUS_NATIVE, _base=BaseException, _group=BaseExceptionGroup, _stop=AuditCensusStop, _dep_clock=_census_clock, _dep_record=_census_record, _phases=_CENSUS_PHASES):
    _native_0 = _native[0]
    if not _state['inflight']:
        return None
    _dep_record(name, start, _dep_clock())
    index = _phases.index(name)
    _state['phase'] = _phases[index + 1] if index + 1 < _native_0(_phases) else None
    return _dep_clock()

def _census_entry_end(start, _state=_CENSUS, _io=_CENSUS_IO, _native=_CENSUS_NATIVE, _base=BaseException, _group=BaseExceptionGroup, _stop=AuditCensusStop, _dep_clock=_census_clock, _dep_record=_census_record):
    if _state['inflight']:
        _dep_record('entry_total', start, _dep_clock())

def _census_emit(reason, _state=_CENSUS, _io=_CENSUS_IO, _native=_CENSUS_NATIVE, _base=BaseException, _group=BaseExceptionGroup, _stop=AuditCensusStop, _dep_clock=_census_clock, _dep_error=_census_error):
    _native_0 = _native[0]
    _native_4 = _native[4]
    _native_5 = _native[5]
    _native_6 = _native[6]
    _native_7 = _native[7]
    try:
        snapshot = _dep_clock()
        frame = _native_6(schema='staged_saved_F_audit_census_v1', seq=_state['seq'] + 1, reason=reason, limit=64, active=_state['active'], start_clock=_state['start'], snapshot_clock=snapshot, entered=_state['entered'], passed=_state['passed'], rejected=_state['rejected'], observed=_state['observed'], inflight=_state['inflight'], phase=_state['phase'], last_incomplete=_state['last_incomplete'], buckets={name: _native_7(row) for name, row in _state['buckets'].items()}, diagnostic_error_count=_native_0(_state['errors']), cache_items=_native_0(_state['cache_ref']), cache_new=_native_0(_state['cache_ref']) - _state['cache_base'], machinery_stage=_state['stage'], installation_seen=_state['installed'])
        raw = (_io[3](('census', frame), sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('ascii')
        if _native_0(raw) > 2048 or _state['seq'] >= 12 or _state['bytes'] + _native_0(raw) > 24576:
            raise _native_4('census frame cap')
        if _io[1](raw) != _native_0(raw):
            raise _native_5('short census write')
        _io[2]()
        _state['seq'] += 1
        _state['bytes'] += _native_0(raw)
    except _base as error:
        _dep_error(error)

def _census_raise(primary, _state=_CENSUS, _io=_CENSUS_IO, _native=_CENSUS_NATIVE, _base=BaseException, _group=BaseExceptionGroup, _stop=AuditCensusStop):
    _native_3 = _native[3]
    if not _state['errors']:
        return
    _state['active'] = False
    failure = _group('audit census observation failed', _native_3(_state['errors']))
    if primary is not None:
        raise primary from failure
    raise failure

def _census_observer(event, args, _state=_CENSUS, _io=_CENSUS_IO, _native=_CENSUS_NATIVE, _base=BaseException, _group=BaseExceptionGroup, _stop=AuditCensusStop, _dep_clock=_census_clock, _dep_emit=_census_emit, _dep_raise=_census_raise):
    _native_0 = _native[0]
    if event == 'electricity_grid.audit_census.installed':
        if _native_0(args) == 1 and args[0] is _state['token'] and (_state['installed'] == 0):
            _state['installed'] = 1
        return
    if not _state['active'] or event != 'open':
        return
    boundary = _state['boundary']
    if boundary._busy or _state['inflight'] or (not _state['last_passed']) or (_state['stamp'] != _state['seen_stamp'] + 1):
        _state['active'] = False
        raise _base('census observer order differs')
    _state['seen_stamp'] = _state['stamp']
    _state['observed'] += 1
    if _state['observed'] == 64:
        _state['active'] = False
        _state['reason'] = 'prefix_complete'
        _state['end'] = _dep_clock()
        _dep_emit('prefix_complete')
        _dep_raise(None)
        if _stop.__bases__ != (_base,):
            raise _base('census stop base differs')
        raise _stop('diagnostic_prefix_complete_64')

def _census_start(runtime, _state=_CENSUS, _io=_CENSUS_IO, _native=_CENSUS_NATIVE, _base=BaseException, _group=BaseExceptionGroup, _stop=AuditCensusStop, _dep_clock=_census_clock, _dep_emit=_census_emit, _dep_observer=_census_observer, _dep_raise=_census_raise, _add=sys.addaudithook, _audit=sys.audit):
    _native_0 = _native[0]
    if _state['ever_started']:
        raise _base('single census window required')
    _state['ever_started'] = True
    _state['boundary'] = runtime._boundary
    if not (runtime._namespace._graph_plan[3][4:8] == _io and runtime._boundary._state[0] == 'ACTIVE'):
        raise _base('held census runtime required')
    if _stop.__bases__ != (_base,):
        raise _base('fixed census stop base required')
    _state['cache_base'] = _native_0(runtime._boundary._cache_initial)
    _state['stage'] = runtime._boundary._observed_stage
    _add(_dep_observer)
    _audit('electricity_grid.audit_census.installed', _state['token'])
    if _state['installed'] != 1:
        raise _base('census installation not observed')
    _state['start'] = _dep_clock()
    _state['active'] = True
    _dep_emit('begin')
    _dep_raise(None)

def _census_open_begin(boundary, event, _state=_CENSUS, _io=_CENSUS_IO, _native=_CENSUS_NATIVE, _base=BaseException, _group=BaseExceptionGroup, _stop=AuditCensusStop, _dep_clock=_census_clock, _dep_error=_census_error):
    if not _state['active'] or event != 'open' or boundary._busy or (boundary is not _state['boundary']):
        return None
    try:
        if _state['entered'] >= 64:
            raise _base('census observer did not stop the prefix')
        _state['entered'] += 1
        _state['inflight'] = True
        _state['phase'] = 'identity1'
        _state['last_passed'] = False
    except _base as error:
        _dep_error(error)
    return (_dep_clock(),)

def _census_open_end(boundary, ticket, primary, _state=_CENSUS, _io=_CENSUS_IO, _native=_CENSUS_NATIVE, _base=BaseException, _group=BaseExceptionGroup, _stop=AuditCensusStop, _dep_clock=_census_clock, _dep_emit=_census_emit, _dep_raise=_census_raise, _dep_record=_census_record):
    if ticket is None:
        return
    _dep_record('audit_body_inclusive', ticket[0], _dep_clock())
    passed = primary is None and boundary._state[0] == 'ACTIVE' and boundary._state[1] and (not boundary._busy)
    if passed:
        _state['stage'] = boundary._observed_stage
    _state['passed' if passed else 'rejected'] += 1
    _state['stamp'] += 1
    _state['last_passed'] = passed
    if _state['phase'] is not None:
        _state['last_incomplete'] = _state['phase']
    _state['inflight'] = False
    _state['phase'] = None
    if passed and _state['passed'] in (1, 8, 16, 24, 32, 40, 48, 56):
        _dep_emit('progress')
    _dep_raise(primary)

def _census_finish(reason, primary, _state=_CENSUS, _io=_CENSUS_IO, _native=_CENSUS_NATIVE, _base=BaseException, _group=BaseExceptionGroup, _stop=AuditCensusStop, _dep_clock=_census_clock, _dep_emit=_census_emit, _dep_raise=_census_raise):
    was_active = _state['active']
    _state['active'] = False
    if was_active:
        _state['reason'] = reason
        _state['end'] = _dep_clock()
        _dep_emit(reason)
    _dep_raise(primary)
def require(value,message):
    if not value:raise ValueError(message)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def parse(raw):return json.loads(raw)
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def digest(value):return sha256(canonical(value)).hexdigest()

def verify_bootstrap_import_identities(rows,_type=type,_vars=vars,_reject=ValueError,_tuple=tuple,_sorted=sorted):
    for namespace,name,value,metadata in rows:
        current=namespace if _type(namespace) is dict else _vars(namespace)
        if name=='__expected_keyset__':
            if _tuple(_sorted(current))!=value:raise _reject('B_S helper keyset changed')
        elif name not in current or current[name] is not value:raise _reject('B_S helper expected binding changed')
    return rows

def verify_bootstrap_import_bindings(rows,_type=type,_vars=vars,_reject=ValueError,_tuple=tuple,_sorted=sorted):
    for namespace,name,value,metadata in rows:
        current=namespace if _type(namespace) is dict else _vars(namespace)
        if name=='__expected_keyset__':
            if _tuple(_sorted(current))!=value:raise _reject('B_S helper keyset changed')
            continue
        if name not in current or current[name] is not value:raise _reject('B_S helper expected binding changed')
        if metadata is not None:
            code,defaults,kw,closure=metadata
            actual_kw=None if value.__kwdefaults__ is None else _tuple(_sorted(value.__kwdefaults__.items()))
            if not (value.__code__ is code and value.__defaults__ is defaults and actual_kw==kw and value.__closure__ is closure):
                raise _reject('B_S helper expected callable changed')
    return rows

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


def open_bootstrap_import_boundary(policy_raw,runtime,expected_bindings,_code=verify_bootstrap_import_bindings.__code__,
        _defs=verify_bootstrap_import_bindings.__defaults__,_fn=FunctionType,_ctx=globals()):
    _fn(_code,_ctx,'held_factory_B_S_roots',_defs)(expected_bindings)
    runtime.entry();require(runtime._boundary_bindings[4] is expected_bindings,'original bootstrap B_S proof required');profile=parse(policy_raw);data=_saved_import_inputs(policy_raw)
    require(profile['schema']=='staged_saved_F_bootstrap_dependency_import_policy_v1','versioned B_S policy required')
    require(sys.getprofile() is None and sys.gettrace() is None and set(sys._current_frames())=={get_ident()},'single unprofiled B_S thread required')
    entry=profile['allowed_entry_module'];module=runtime._namespace.module
    require(sys.modules.get(entry['name']) is module and Path(module.__file__)==Path(entry['path']) and module is not sys.modules['__main__'],'exact held ENTRY namespace required')
    require(not any(name!=entry['name'] and any(name==p or name.startswith(p+'.') for p in profile['required_cold_prefixes']) for name in sys.modules),'B_S dependencies must be cold')
    require(tuple((v.__module__,v.__name__) for v in sys.meta_path)==(('_frozen_importlib','BuiltinImporter'),('_frozen_importlib','FrozenImporter'),('_frozen_importlib_external','PathFinder')),'exact baseline B3 required')
    require(tuple(sys.path)==tuple(profile['initial_paths']) and sys.flags.safe_path and sys.flags.no_site and sys.flags.no_user_site,'exact B_S startup paths/flags required')
    guard=object.__new__(BootstrapImportBoundary);token=object();finder_plan=_saved_import_finder_plan(data,profile)
    audit_fn=BootstrapImportBoundary._audit
    def audit_hook(event,args):audit_fn(guard,event,args,token,expected_bindings)
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
        _state=('NEW',True,0,0,0,0,False,''),_internal=None,_busy=False,_adapter=None,_adapter_bindings=(),_source_raw=None,_failure=None,_first_error=None,
        _runtime=runtime,_path_stage=0,_load_started=False,_cache_initial=tuple(sys.path_importer_cache.items()),_module_initial=tuple(sys.modules.items()),_policy_profile=profile,
        _admitted_paths=tuple(profile['admitted_paths']),_runtime_bindings=(),_retention=(),_handoff_seen=0,_adapter_graph=None,_expected_bindings=expected_bindings,_protected_functions=(*tuple(value for _,_,value,metadata in expected_bindings if metadata is not None),audit_hook))
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


def trace_import_stage(runtime,stage):
    clock,write,flush,dumps=runtime._namespace._graph_plan[3][4:8]
    write((dumps(('stage',stage,clock()),separators=(',',':'))+'\n').encode('ascii'));flush()

def diagnostic_import_once(runtime,_importer=importlib.import_module,_base=BaseException,_group=BaseExceptionGroup,_stop=AuditCensusStop,
        _start=_census_start,_finish=_census_finish,_trace=trace_import_stage):
    _trace(runtime,'before_adapter_import');primary=None
    try:
        _start(runtime)
        result=_importer('src.staged_rts24_saved_fresh_adoption_v1')
        _trace(runtime,'adapter_import_returned')
        _finish('import_return_before64',None)
        raise _stop('diagnostic_import_return_before64')
    except _base as error:primary=error;raise
    finally:
        cleanup=[]
        try:_finish('import_error_before64',primary)
        except _base as error:cleanup.append(error)
        try:_trace(runtime,'after_adapter_import_attempt')
        except _base as error:cleanup.append(error)
        if cleanup:
            group=_group('import diagnostic cleanup failed',cleanup)
            if primary is not None:raise primary from group
            raise group

def load_bootstrap_adapter(runtime,boundary,_code=verify_bootstrap_import_bindings.__code__,
        _defs=verify_bootstrap_import_bindings.__defaults__,_fn=FunctionType,_ctx=globals()):
    _fn(_code,_ctx,'held_loader_B_S_roots',_defs)(runtime._boundary_bindings[4])
    runtime.entry()
    require(runtime._boundary is boundary and boundary.phase()=='PATH6','exact path-admitted runtime boundary required')
    trace_import_stage(runtime,'loader_ready')
    expected=runtime.source_bookend();boundary.begin_import()
    adapter=diagnostic_import_once(runtime)
    boundary.authenticate_machinery();trace_import_stage(runtime,'machinery_authenticated')
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
    trace_import_stage(runtime,'before_adapter_roots')
    proof=freeze_adapter_roots(adapter,raw,runtime);object.__setattr__(boundary,'_adapter_graph',proof);object.__setattr__(boundary,'_commit',digest(boundary._image()))
    trace_import_stage(runtime,'after_adapter_roots')
    runtime.source_bookend();object.__setattr__(boundary,'_source_raw',canonical(expected));object.__setattr__(boundary,'_commit',digest(boundary._image()))
    require(all(name in sys.modules and sys.modules[name] is module for name,module in boundary._module_initial),'initial B_S modules changed')
    require(len(sys.modules)<=4096,'runtime module retention cap')
    object.__setattr__(boundary,'_retention',tuple(sys.modules.items()));object.__setattr__(boundary,'_commit',digest(boundary._image()))
    sys.audit('electricity_grid.B_S.adapter_authenticated',adapter)
    trace_import_stage(runtime,'before_boundary_close');boundary.close();trace_import_stage(runtime,'after_boundary_close')
    return adapter,boundary._runtime_bindings,boundary._retention
class BootstrapImportRejected(RuntimeError): pass


class _SavedImportCPUQueryDenied(OSError): pass


class _SavedImportFrameMarker(Exception): pass


class BootstrapImportUnresolved(RuntimeError):
    def __init__(self,boundary,primary,cleanup):
        self.boundary,self.primary,self.cleanup=boundary,primary,tuple(cleanup)
        super().__init__('successor dependency import did not complete')
    def __reduce__(self):raise TypeError('import failure retains local state')

def make_bootstrap_import_failure(boundary,primary,cleanup,_class=BootstrapImportUnresolved,_new=RuntimeError.__new__,
        _init=RuntimeError.__init__,_put=object.__setattr__,_tuple=tuple):
    error=_new(_class);_init(error,'successor dependency import did not complete')
    _put(error,'boundary',boundary);_put(error,'primary',primary);_put(error,'cleanup',_tuple(cleanup))
    return error


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
    __slots__=('_profile_raw', '_creator', '_namespace', '_global_bindings', '_attribute_bindings', '_own_bindings', '_owner', '_owner_commit', '_lock', '_codes', '_numpy_path', '_numpy_state', '_paths', '_event_sets', '_import_machinery', '_machinery_base', '_finder_plan', '_finder_bindings', '_finder_authenticated', '_observed_stage', '_authenticated_stage', '_state', '_internal', '_busy', '_adapter', '_adapter_bindings', '_source_raw', '_commit', '_failure', '_first_error', '_runtime', '_path_stage', '_load_started', '_cache_initial', '_module_initial', '_policy_profile', '_admitted_paths', '_runtime_bindings', '_retention', '_handoff_seen', '_adapter_graph', '_expected_bindings', '_protected_functions')
    def __setattr__(self,name,value):raise AttributeError("import boundary fields are frozen")
    def __delattr__(self,name):raise AttributeError("import boundary fields are frozen")
    def claim_pending(self,runtime):
        self._entry()
        require(self._runtime is runtime and runtime._boundary is None and runtime._phase=='ADOPTED'
            and self._state==('INSTALLING',True,0,0,0,0,False,'') and self._path_stage==0 and not self._load_started
            and self._handoff_seen==0 and self._adapter is None and not self._runtime_bindings and not self._retention,
            'exact prepared pending boundary required')
        creator,callback,token=self._ownership()
        require(callback.__globals__ is self._namespace and callback.__code__.co_freevars==('audit_fn','expected_bindings','guard','token')
            and callback.__closure__[0].cell_contents is type(self)._audit and callback.__closure__[1].cell_contents is self._expected_bindings
            and callback.__closure__[2].cell_contents is self and callback.__closure__[3].cell_contents is token,
            'original pending callback closure required')
        return self
    def _check_cache(self):
        current=sys.path_importer_cache;before=dict(self._cache_initial)
        for key,value in before.items():
            require(key in current and current[key] is value ,'predecessor importer cache changed')
        roots=(str(ROOT),str(EXE.parent));root_paths=None
        for key,value in current.items():
            if key in before:continue
            admitted=False
            if type(key) is str and os.path.isabs(key):
                path=Path(key)
                if root_paths is None:root_paths=tuple(Path(root) for root in roots)
                admitted=any(path.is_relative_to(root) for root in root_paths)
            require(admitted,'importer cache key outside admitted roots')
            require(value is None or type(value) is machinery.FileFinder and value.path==key,'new importer cache kind differs')
    def phase(self):
        state=self._state[0]
        if state!='ACTIVE':return state
        if self._authenticated_stage==2:return 'AUTHENTICATED'
        if self._observed_stage==2:return 'D_SEEN'
        if self._observed_stage==1:return 'M_SEEN'
        if self._load_started:return 'IMPORTING'
        return 'ACTIVE_B3' if self._path_stage==0 else 'PATH6'
    def admit_paths(self):
        self._entry();require(self.phase()=='ACTIVE_B3' and self._runtime._audit_handed_off,'active handed-off B_S path transition required')
        require(tuple(sys.path)==tuple(self._policy_profile['initial_paths']),'fixed B_S initial paths required')
        sys.audit('electricity_grid.B_S.path_prepared',self)
        object.__setattr__(self,'_path_stage',1);sys.path.extend(self._admitted_paths[4:]);object.__setattr__(self,'_commit',digest(self._image()))
        sys.audit('electricity_grid.B_S.path_committed',self);return self._entry()
    def begin_import(self):
        self._entry();require(self.phase()=='PATH6' and not self._load_started,'single B_S import episode required')
        object.__setattr__(self,'_load_started',True);object.__setattr__(self,'_commit',digest(self._image()));sys.audit('electricity_grid.B_S.import_begin',self)
        return self
    def profile_raw(self):
        self._entry();require(self._state[0]=='CLOSED','completed import profile required')
        modules=[]
        for name,module in sorted(sys.modules.items()):
            if type(module) is ModuleType:
                namespace=vars(module);spec=namespace.get('__spec__');loader=namespace.get('__loader__')
                origin=getattr(spec,'origin',None) if type(spec) is machinery.ModuleSpec else None
                modules.append((name,'module',namespace.get('__file__'),origin,type(loader).__module__+'.'+type(loader).__qualname__))
            else:modules.append((name,'opaque',type(module).__module__+'.'+type(module).__qualname__))
        require(len(modules)<=4096 and len(sys.path_importer_cache)<=4096,'B_S retention observation cap')
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
    def __new__(cls,*a,**k):raise TypeError('open the fixed successor import policy explicitly')
    def __init_subclass__(cls,**kw):raise TypeError('exact successor import policy type required')
    def _image(self):
        return (id(self._expected_bindings),id(self._protected_functions),id(self._adapter_graph),id(self._runtime_bindings),id(self._retention),self._handoff_seen,id(self._runtime),self._path_stage,self._load_started,id(self._cache_initial),id(self._module_initial),id(self._policy_profile),self._admitted_paths,pin(self._profile_raw),self._creator,id(self._namespace),
            tuple((n,id(v),id(code),id(defaults),pin(kw) if type(kw) is bytes else None,id(closure)) for n,v,code,defaults,kw,closure in self._global_bindings),
            tuple((id(m),n,id(v)) for m,n,v in self._attribute_bindings),
            tuple((n,id(fn),id(code),id(defaults),pin(kw),id(closure)) for n,fn,code,defaults,kw,closure in self._own_bindings),
            self._owner_commit,id(self._lock),tuple(id(code) for code in self._codes),self._numpy_path,
            None if self._numpy_state is None else (id(self._numpy_state[0]),self._numpy_state[1]),self._paths,self._event_sets,self._import_machinery,
            id(self._machinery_base),id(self._finder_plan),id(self._finder_bindings),id(self._finder_authenticated),self._observed_stage,self._authenticated_stage,
            self._state,id(self._adapter),tuple((n,id(fn),id(code)) for n,fn,code in self._adapter_bindings),
            pin(self._source_raw) if self._source_raw is not None else None,id(self._failure),id(self._first_error))
    def _ownership(self,_code=verify_bootstrap_import_identities.__code__,_defs=verify_bootstrap_import_identities.__defaults__,_fn=FunctionType,_ctx=globals(),_reject=ValueError,_require=require):
        if self._expected_bindings is not self._runtime._boundary_bindings[4]:raise _reject('original B_S expected proof required')
        _fn(_code,_ctx,'held_owner_B_S_roots',_defs)(self._expected_bindings)
        creator,callback,token,code=self._owner
        _require(creator==self._creator and self._owner_commit==digest((creator,id(callback),id(code),id(token))),
            'import guard ownership changed')
        return creator,callback,token
    def _finder_class_shape(self,cls,spec):
        name,doc,registry,methods=spec
        require(type(cls) is type and cls.__bases__==(object,) and cls.__name__==cls.__qualname__==name,'fixed finder class differs')
        namespace=vars(cls);expected={'__module__','__doc__','__dict__','__weakref__',*(m[0] for m in methods)}
        if registry is not None:expected.add(registry)
        require(set(namespace) in (expected,expected|{'__qualname__'}) and namespace['__doc__']==doc,'fixed finder class fields differ')
        functions=tuple((name,namespace[name]) for name,code,count in methods)
        require(all(type(fn) is FunctionType for name,fn in functions),'fixed finder functions required')
        return functions
    def _hold_finder(self,plan,finder):
        tag,module_name,path,finder_name,loader_name,registry_name,singleton,classes,extra=plan
        module=sys.modules.get(module_name)
        require(type(module) is ModuleType,'fixed finder module required');namespace=vars(module)
        require(type(namespace.get('__file__')) is str and Path(namespace['__file__']).absolute()==Path(path),'fixed finder module path differs')
        cls=namespace.get(finder_name)
        require(type(finder) is cls and type(vars(finder)) is dict and not vars(finder),'exact empty finder instance required')
        held=[]
        for spec in classes:
            current=namespace.get(spec[0]);functions=self._finder_class_shape(current,spec)
            require(vars(current)['__module__']==module_name,'fixed finder class module differs')
            held.append((spec,current,functions))
        registry=vars(cls)[registry_name];require(type(registry) is dict,'finder registry object required')
        names=('sys','importlib',finder_name,loader_name)+(('NOTSET','deprecation_warning') if tag=='M' else (singleton,))
        require(all(n in namespace for n in names) and namespace['sys'] is sys and namespace['importlib'] is self._machinery_base[8],'finder globals differ')
        if singleton is not None:require(namespace[singleton] is finder,'finder singleton differs')
        return (plan,module,namespace,finder,registry,tuple(held),tuple((n,namespace[n]) for n in names))
    def _check_finder_structure(self,binding):
        plan,module,namespace,finder,registry,classes,globals_held=binding
        require(sys.modules.get(plan[1]) is module and vars(module) is namespace,'finder module identity differs')
        require(type(namespace.get('__file__')) is str and Path(namespace['__file__']).absolute()==Path(plan[2]),'finder module path changed')
        require(type(finder) is classes[0][1] and type(vars(finder)) is dict and not vars(finder),'finder instance changed')
        require(vars(type(finder)).get(plan[5]) is registry,'finder registry identity changed')
        for name,value in globals_held:require(namespace.get(name) is value,'finder global identity changed')
        for spec,cls,functions in classes:
            require(namespace.get(spec[0]) is cls and vars(cls)['__module__']==plan[1],'finder class identity changed')
            current=self._finder_class_shape(cls,spec)
            require(all(n==m and fn is original for (n,fn),(m,original) in zip(current,functions)),'finder method identity changed')
    def _observe_machinery(self):
        try:
            base=self._machinery_base
            require(sys.meta_path is base[3] and sys.path_hooks is base[4] and sys.path is base[5]
                and sys.path_importer_cache is base[6] and sys.modules is base[7],'machinery container changed')
            require(tuple(map(id,sys.path_hooks))==tuple(map(id,base[1])) and tuple(sys.path)==(base[2] if self._path_stage==0 else self._admitted_paths),'machinery hooks/path changed')
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
            require(self._authenticated_stage in (0,2),'finder authentication stage differs')
            if self._authenticated_stage==0:
                require(not self._finder_authenticated,'pending finder code bindings differ');return
            require(self._observed_stage==2 and self._finder_authenticated,'authenticated finder sequence differs')
            for fn,code,defaults,namespace,expected,count in self._finder_authenticated:
                require(fn.__globals__ is namespace and fn.__code__ is code and code==expected and fn.__defaults__ is defaults
                    and (defaults is None if count==0 else type(defaults) is tuple and defaults==(None,)*count)
                    and fn.__kwdefaults__ is None and fn.__closure__ is None,'authenticated finder function changed')
        except BootstrapImportRejected:raise
        except BaseException as error:self._fault('finder_authentication',error)
    def authenticate_machinery(self):
        """Called once by the loader outside the audit callback, after dependency import."""
        if self._state[6]:raise ValueError('terminal import authentication cannot restart')
        try:
            require(not self._busy and self._state[0]=='ACTIVE','active non-audit finder authentication required')
            self._audit_entry();require(self._observed_stage==2 and self._authenticated_stage==0,'complete pending finder transition required')
            authenticated=[]
            for plan,module,namespace,finder,registry,classes,globals_held in self._finder_bindings:
                for spec,cls,functions in classes:
                    for (name,fn),(expected_name,expected,count) in zip(functions,spec[3]):
                        require(name==expected_name and fn.__globals__ is namespace and fn.__code__==expected
                            and (fn.__defaults__ is None if count==0 else type(fn.__defaults__) is tuple and fn.__defaults__==(None,)*count)
                            and fn.__kwdefaults__ is None and fn.__closure__ is None,'fixed finder source function differs')
                        authenticated.append((fn,fn.__code__,fn.__defaults__,namespace,expected,count))
                for name,expected,count in plan[8]:
                    fn=namespace[name]
                    require(type(fn) is FunctionType and fn.__globals__ is namespace and fn.__code__==expected
                        and (fn.__defaults__ is None if count==0 else type(fn.__defaults__) is tuple and fn.__defaults__==(None,)*count)
                        and fn.__kwdefaults__ is None and fn.__closure__ is None,'fixed finder global function differs')
                    authenticated.append((fn,fn.__code__,fn.__defaults__,namespace,expected,count))
            object.__setattr__(self,'_finder_authenticated',tuple(authenticated));object.__setattr__(self,'_authenticated_stage',2);object.__setattr__(self,'_commit',digest(self._image()))
            self._check_finder_authentication();return self
        except BootstrapImportRejected:raise
        except BaseException as error:self._fault('finder_authentication',error)
    def _audit_entry(self,_code=verify_bootstrap_import_identities.__code__,_defs=verify_bootstrap_import_identities.__defaults__,_fn=FunctionType,_ctx=globals(),_reject=ValueError,_require=require,
            _tick=_census_clock,_cut=_census_cut,_end=_census_entry_end,_stats=_CENSUS):
        census_start=_tick() if _stats['inflight'] else None;census_tick=census_start
        try:
            if self._expected_bindings is not self._runtime._boundary_bindings[4]:raise _reject('original B_S expected proof required')
            _fn(_code,_ctx,'held_audit_B_S_identity_roots',_defs)(self._expected_bindings)
            census_tick=_cut('identity1',census_tick)
            _require(self._runtime._resource.owner is self._runtime and self._runtime._namespace.module is sys.modules.get(self._policy_profile['allowed_entry_module']['name']),'actual runtime/namespace link changed')
            census_tick=_cut('runtime_link',census_tick)
            self._check_cache()
            census_tick=_cut('cache',census_tick)
            for name,value,*_ in self._global_bindings:_require(self._namespace.get(name) is value,'import module binding changed')
            for module,name,value in self._attribute_bindings:_require(getattr(module,name) is value,'import system binding changed')
            census_tick=_cut('globals_attrs',census_tick)
            self._ownership()
            census_tick=_cut('ownership',census_tick)
            _require(self._creator==(os.getpid(),get_ident()) and self._commit==digest(self._image()),'original import guard required')
            census_tick=_cut('image_digest',census_tick)
            self._observe_machinery()
            census_tick=_cut('machinery',census_tick)
            return self
        finally:_end(census_start)
    def _entry(self,_code=verify_bootstrap_import_bindings.__code__,_defs=verify_bootstrap_import_bindings.__defaults__,_fn=FunctionType,_ctx=globals(),_reject=ValueError,_require=require):
        if self._expected_bindings is not self._runtime._boundary_bindings[4]:raise _reject('original B_S expected proof required')
        _fn(_code,_ctx,'held_entry_B_S_roots',_defs)(self._expected_bindings)
        self._audit_entry()
        _require(self._owner[1].__code__ is self._owner[3],'import callback changed')
        _require(len(self._profile_raw)==4745 and sha256(self._profile_raw).hexdigest()=='4b731fc38ed2b52bff727acf0b02e4b8da7396cb17f2354225b34348155d9e9c','fixed import policy changed')
        self._check_finder_authentication()
        for name,fn,code,defaults,kw,closure in self._global_bindings:
            _require(self._namespace.get(name) is fn,'import module binding changed')
            if code is not None:_require(fn.__code__ is code and fn.__defaults__ is defaults and canonical(fn.__kwdefaults__)==kw and fn.__closure__ is closure,'import helper changed')
        for module,name,value in self._attribute_bindings:_require(getattr(module,name) is value,'import system binding changed')
        for name,fn,code,defaults,kw,closure in self._own_bindings:
            _require(getattr(type(self),name) is fn and fn.__code__ is code and fn.__defaults__ is defaults
                and canonical(fn.__kwdefaults__)==kw and fn.__closure__ is closure,'import guard method changed')
        for name,fn,code in self._adapter_bindings:_require(getattr(self._adapter,name) is fn and fn.__code__ is code,'imported direct adapter binding changed')
        if self._adapter_graph is not None:check_adapter_roots(self._adapter,self._adapter_graph)
        if self._numpy_state is not None:
            module,value=self._numpy_state
            _require(sys.modules.get('numpy.testing._private.utils') is module and type(module) is ModuleType
                and Path(module.__file__).absolute()==Path(self._numpy_path) and value is False and module._SUPPORTS_SVE is False,
                'NumPy fallback value bookend differs')
        return self
    def _fault(self,reason,original=None,_error=BootstrapImportRejected,_put=object.__setattr__):
        error=_error('dependency import rejected: '+reason)
        if self._first_error is None:_put(self,'_first_error',error if original is None else original)
        old=self._state
        _put(self,'_state',('FAULTED',old[1],old[2],old[3],old[4]+1,old[5],old[6],old[7] or reason))
        # Leave the old commitment invalid; a fault can never become a valid live image.
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
    def _audit(self,event,args,token,expected_bindings,_type=type,_len=len,_str=str,_any=any,_base=BaseException,
            _begin=_census_open_begin,_end=_census_open_end,_group=BaseExceptionGroup):
        census_ticket=_begin(self,event);census_primary=None
        try:
            if not self._state[1]:return
            process,process_prefixes,mutations=self._event_sets
            function_mutation=event in ('object.__setattr__','object.__delattr__') and _len(args)>=2 and _type(args[1]) is _str and args[1] in ('__code__','__defaults__','__kwdefaults__') and (
                _any(args[0] is value for _,_,value,metadata in expected_bindings if metadata is not None) or args[0] is self._owner[1] or _any(args[0] is value for binding in self._finder_bindings for value in (
                    *(fn for spec,cls,functions in binding[5] for name,fn in functions),*(value for name,value in binding[6]))))
            if function_mutation:self._fault('helper_or_finder_function_mutation')
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
                except _base as error:self._fault('classification_error',error)
                finally:object.__setattr__(self,'_busy',False)
        except _base as census_error:
            census_primary=census_error;raise
        finally:
            try:_end(self,census_ticket,census_primary)
            except _base as census_secondary:
                if census_primary is not None and census_secondary is not census_primary:
                    raise census_primary from _group('audit census cleanup failed',(census_secondary,))
                raise
    def close(self,primary=None,_code=verify_bootstrap_import_bindings.__code__,_defs=verify_bootstrap_import_bindings.__defaults__,
            _fn=FunctionType,_ctx=globals(),_base=BaseException,_put=object.__setattr__,_failure=make_bootstrap_import_failure,_digest=digest):
        if self._state[6]:
            if self._failure is not None:raise self._failure
            return
        errors=[];roots_ok=False
        try:
            _fn(_code,_ctx,'held_close_B_S_roots',_defs)(self._expected_bindings)
            self._entry();creator,callback,token=self._ownership();roots_ok=True
        except _base as error:errors.append(('bindings',error))
        old=self._state;_put(self,'_state',(*old[:6],True,old[7]))
        if roots_ok:
            try:
                _put(self,'_commit',_digest(self._image()))
                try:_saved_import_inputs(self._profile_raw)
                except _base as error:errors.append(('external_bookend',error))
                if set(sys._current_frames())!={creator[1]}:errors.append(('threads',ValueError('extra Python import thread')))
                if sys.getprofile() is not None or sys.gettrace() is not None:errors.append(('tracing',ValueError('import profile/trace remained active')))
                if self._state[2:5]!=(1,1,0) or self._state[0]!='ACTIVE' or self._numpy_state is None or self._observed_stage!=2 or self._authenticated_stage!=2 or self._handoff_seen!=1:
                    errors.append(('policy_terminal',ValueError('import policy did not complete')))
                if self._first_error is not None and self._first_error is not primary:errors.insert(0,('audit_primary',self._first_error))
                if not errors:
                    try:self._entry()
                    except _base as error:errors.append(('terminal_bookend',error))
            except _base as error:errors.append(('close_control',error))
        failed=primary is not None or bool(errors)
        _put(self,'_state',('FAULTED' if failed else 'CLOSED',False,*self._state[2:6],True,self._state[7]))
        if failed:_put(self,'_failure',_failure(self,primary,errors))
        if roots_ok:
            try:_put(self,'_commit',_digest(self._image()))
            except _base as error:
                _put(self,'_state',('FAULTED',False,*self._state[2:6],True,self._state[7]));errors.append(('close_commit',error))
                _put(self,'_failure',_failure(self,primary,errors));failed=True
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
