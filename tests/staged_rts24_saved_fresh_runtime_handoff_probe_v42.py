"""Held bootstrap coordinator for local ownership and import-only diagnostics."""
def failure_owner(error):
    owner=getattr(error,'owner',None)
    return owner if type(owner) is LocalRuntimeInputs else None

def validate_import_helper(helper,unit,native_builtins,census_io,held_bridge):
    native={name:value for name,value in native_builtins}
    (type,vars,len,tuple,sorted,dict,set,all,staticmethod,classmethod,property,object,ValueError,BaseException,any,str)=(native[name] for name in ('type','vars','len','tuple','sorted','dict','set','all','staticmethod','classmethod','property','object','ValueError','BaseException','any','str'))
    def require(value,message):
        if not value:raise ValueError(message)
    current=vars(builtins)
    require(len(current)==len(native) and all(name in current and current[name] is value for name,value in native_builtins),'complete native builtins changed')
    namespace=vars(helper);require(namespace['__builtins__'] is current,'original B_S builtins dict required')
    require(type(held_bridge) is tuple and len(held_bridge)==3 and namespace.get('_PROJECT_BRIDGE') is held_bridge,'original held project bridge required')
    classes={'BootstrapImportRejected','_SavedImportCPUQueryDenied','_SavedImportFrameMarker','BootstrapImportUnresolved','BootstrapImportBoundary','AuditCensusStop'}
    require(namespace['_CENSUS_IO'] is census_io and namespace['_CENSUS_DUMPS'] is census_io[3],'held census IO roots differ')
    require(namespace['_CENSUS_NATIVE']==tuple(native[n] for n in ('len','type','max','tuple','ValueError','OSError','dict','list','float')),'census native roots differ')
    require(namespace['AuditCensusStop'].__bases__==(BaseException,),'fixed census stop base required')
    census_defaults=dict(_state=namespace['_CENSUS'],_io=census_io,_native=namespace['_CENSUS_NATIVE'],_base=BaseException,
        _group=native['BaseExceptionGroup'],_stop=namespace['AuditCensusStop'],_phases=namespace['_CENSUS_PHASES'],_add=sys.addaudithook,_audit=sys.audit,_pid=os.getpid,_ident=get_ident)
    def check(fn,code,cls=None):
        require(type(fn) is FunctionType and fn.__globals__ is namespace and fn.__code__==code,'B_S source callable differs')
        if code.co_name.startswith('_census_'):
            names=code.co_varnames[code.co_varnames.index('_state'):code.co_argcount]
            expected=tuple(namespace['_census_'+name[5:]] if name.startswith('_dep_') else census_defaults[name] for name in names)
        elif code.co_name in ('verify_bootstrap_import_bindings','verify_bootstrap_import_identities'):expected=(type,vars,ValueError,tuple,sorted)
        elif code.co_name in ('_audit_entry','_ownership','_entry'):
            reader=namespace['verify_bootstrap_import_bindings'] if code.co_name=='_entry' else namespace['verify_bootstrap_import_identities']
            expected=(reader.__code__,reader.__defaults__,FunctionType,namespace,ValueError,namespace['require'])
            if code.co_name=='_audit_entry':expected+=tuple(namespace[n] for n in ('_census_clock','_census_cut','_census_entry_end','_CENSUS'))+(cls._image,cls._observe_machinery)
        elif code.co_name=='project_bridge_call':expected=(FunctionType,type,len,ValueError,tuple)
        elif code.co_name=='load_bootstrap_adapter':
            expected=(namespace['verify_bootstrap_import_bindings'].__code__,namespace['verify_bootstrap_import_bindings'].__defaults__,FunctionType,namespace,
                namespace['project_bridge_call'].__code__,namespace['project_bridge_call'].__defaults__,held_bridge)
        elif code.co_name=='_observe_machinery':expected=(cls._image,)
        elif code.co_name=='_image':expected=(native['id'],)
        elif code.co_name=='_audit':expected=(type,len,str,any,BaseException,namespace['_census_open_begin'],namespace['_census_open_end'],native['BaseExceptionGroup'])+(cls._image,cls._image.__code__,cls._image.__defaults__,native['id'],cls._audit_entry,namespace['_POST_METRICS'],(dict,native['int'],native['bool']),ValueError,FunctionType,namespace['project_bridge_call'].__code__,namespace['project_bridge_call'].__defaults__,held_bridge)
        elif code.co_name in ('authenticate_machinery','_check_finder_authentication','check_adapter_roots','profile_raw'):expected=(namespace['_POST_METRICS'],census_io[0],native['max'],BaseException,native['BaseExceptionGroup'])
        elif code.co_name=='_fault':expected=(None,namespace['BootstrapImportRejected'],object.__setattr__)
        elif code.co_name=='diagnostic_import_once':expected=(namespace['importlib'].import_module,BaseException,native['BaseExceptionGroup'],namespace['AuditCensusStop'],namespace['_census_start'],namespace['_census_finish'],namespace['trace_import_stage'],namespace['_POST_METRICS'])
        elif code.co_name=='make_bootstrap_import_failure':expected=(namespace['BootstrapImportUnresolved'],native['RuntimeError'].__new__,native['RuntimeError'].__init__,object.__setattr__,tuple)
        elif code.co_name=='close':expected=(None,namespace['verify_bootstrap_import_bindings'].__code__,namespace['verify_bootstrap_import_bindings'].__defaults__,FunctionType,namespace,BaseException,object.__setattr__,namespace['make_bootstrap_import_failure'],namespace['digest'])
        elif code.co_name in ('open_bootstrap_import_boundary',):expected=(namespace['verify_bootstrap_import_bindings'].__code__,namespace['verify_bootstrap_import_bindings'].__defaults__,FunctionType,namespace)
        else:expected=fn.__defaults__ if fn.__defaults__ is None or fn.__defaults__==(None,) else ()
        require(fn.__defaults__==expected,'B_S source defaults differ')
        require(fn.__kwdefaults__ is None,'B_S source keyword defaults differ')
        if code.co_freevars==('__class__',):require(fn.__closure__[0].cell_contents is cls,'B_S source class cell differs')
        else:require(fn.__closure__ is None,'B_S source closure differs')
    for code in unit.co_consts:
        if type(code) is not CodeType or code.co_name.startswith('<'):continue
        obj=namespace[code.co_name]
        if code.co_name in classes:
            require(type(obj) is type and obj.__module__==helper.__name__,'B_S source class differs')
            for method in code.co_consts:
                if type(method) is not CodeType or method.co_name.startswith('<'):continue
                member=vars(obj)[method.co_name]
                if type(member) in (staticmethod,classmethod):member=member.__func__
                if type(member) is property:member=member.fget
                check(member,method,obj)
        else:check(obj,code)
    syntax=sys.modules['ast'];dis=sys.modules['dis'];imports=sys.modules['importlib'];RLock=vars(sys.modules['threading'])['RLock']
    fixed=dict(ast=syntax,sha256=sha256,importlib=imports,util=imports.util,machinery=imports.machinery,json=json,os=os,
        Path=Path,subprocess=subprocess,sys=sys,get_ident=get_ident,RLock=RLock,ModuleType=type(sys),FunctionType=FunctionType,CodeType=CodeType,_READ_FILE=read_file)
    require(all(namespace.get(name) is value for name,value in fixed.items()),'B_S bootstrap imported root differs')
    require(namespace['ROOT']==ROOT and namespace['EXE']==EXE,'B_S bootstrap constants differ')
    stores={op.argval for op in dis.get_instructions(unit) if op.opname=='STORE_NAME'}
    require(set(namespace)==stores|{'__name__','__file__','__package__','__loader__','__spec__','__builtins__','_READ_FILE'},'B_S bootstrap namespace keys differ')
    rows=[]
    def capture(context):
        values=context if type(context) is dict else vars(context)
        rows.append((context,'__expected_keyset__',tuple(sorted(values)),None))
        for name,value in tuple(values.items()):
            metadata=None
            if type(value) is FunctionType:
                kw=None if value.__kwdefaults__ is None else tuple(sorted(value.__kwdefaults__.items()))
                metadata=(value.__code__,value.__defaults__,kw,value.__closure__)
            rows.append((context,name,value,metadata))
    capture(namespace)
    for name in classes:capture(namespace[name])
    for module,names in ((sys,('audit','addaudithook','modules','meta_path','path','path_hooks','path_importer_cache','getprofile','gettrace','_current_frames')),
        (imports,('import_module','util','machinery')),(imports.util,('find_spec','spec_from_loader')),(imports.machinery,('ModuleSpec','FileFinder')),
        (builtins,('type','vars','tuple','sorted','object','getattr','id','len','all','any','compile','ValueError','BaseException'))):
        for name in names:rows.append((module,name,vars(module)[name],None))
    rows.append((current,'__expected_keyset__',tuple(sorted(native)),None))
    rows.extend((current,name,value,None) for name,value in native_builtins)
    proof=tuple(rows);namespace['verify_bootstrap_import_bindings'](proof)
    require(len(current)==len(native) and all(name in current and current[name] is value for name,value in native_builtins),'complete native builtins changed')
    return proof

def _probe_main(_compile=compile,_exec=exec,_type=type,_vars=vars,_native_builtins=tuple(vars(builtins).items())):
    native={key:value for key,value in _native_builtins}
    plan=guard=lease=inputs=namespace=ns_helper=bs_helper=runtime=boundary=resource=None
    primary=None;secondary=[];phase='MANIFEST';discovered=None;directory_closed=False;observed_profile=None;was_live=False;observed=None;construction_result=None;namespace_terminal=None;permission_observation=None;bootstrap_actor=None;actor_observation=None;producer_result=None
    ns_close=runtime_close=None
    try:
        out=ROOT/'results/tables/staged_rts24_saved_fresh_complete_bootstrap_native_v2_non_authoritative';path=Path(sys.argv[2])
        require(path.parent==out and path.name.startswith('probe_') and path.name.endswith('.plan.json'),'fixed runtime manifest location')
        raw=read_file(path,dict(bytes=path.lstat().st_size,sha256=sys.argv[3]));plan=check_plan(raw)
        require(path.name=='probe_'+plan['case']+'.plan.json','runtime case/path differs')
        if plan['case']=='discovery':discovered=startup_profile(plan)
        else:
            guard=install_guard(plan);phase='SELF';lease=open_local_pre_entry_lease(raw,guard);resource=lease._resource;inputs=lease.transfer()
            from types import ModuleType
            def native_bookend():
                current=_vars(builtins);require(len(current)==len(native),'runtime builtin keys changed')
                require(all(current.get(k) is v for k,v in native.items()),'runtime builtin changed')
            def helper_load(ref,name,extra):
                held=read_file(ref['path'],ref['pin']);inputs.entry();native_bookend()
                module=ModuleType(name);module.__dict__.update(__file__=ref['path'],**extra)
                code=_compile(held,ref['path'],'exec',dont_inherit=True,optimize=0);_exec(code,_vars(module),_vars(module));native_bookend()
                return module,code
            phase='NAMESPACE'
            ns_helper,unit=helper_load(plan['namespace_helper'],'_saved_F_namespace_helper_timing_v1',dict(_INPUT_TYPE=LocalPreEntryInputs,_RUNTIME_TYPE=LocalRuntimeInputs))
            validate_held_namespace_helper(ns_helper,unit,native,LocalPreEntryInputs,LocalRuntimeInputs,_compile,_exec,_type,_vars)
            bindings=ns_helper.capture_helper_bindings();namespace=ns_helper.open_entry_namespace(inputs,bindings)
            ns_close=(FunctionType,ns_helper.LiveEntryNamespace.close.__code__,vars(ns_helper),ns_helper.LiveEntryNamespace.close.__defaults__)
            census_io=namespace._graph_plan[3][4:8]
            def observer(event,args):
                case=plan['case']
                if event=='electricity_grid.runtime.transfer_prepared' and case=='precommit':raise ValueError('injected_runtime_precommit')
                if event=='electricity_grid.runtime.owner_committed' and case=='postcommit':raise ValueError('injected_runtime_postcommit')
                if event=='sys.addaudithook' and case=='blocked_installation' and runtime is not None and runtime._boundary is not None:raise RuntimeError('injected_B_S_installation_block')
                if event=='electricity_grid.runtime.audit_handoff_between' and case=='handoff_middle':raise ValueError('injected_runtime_audit_handoff_middle')
                if event=='electricity_grid.B_S.finder_stage' and (case=='M_only' and args[0]==1 or case=='after_D' and args[0]==2):raise ValueError('injected_B_S_finder_stage_'+str(args[0]))
            sys.addaudithook(observer);phase='TRANSFER'
            runtime=namespace.transfer_runtime();runtime_close=(FunctionType,LocalRuntimeInputs.close.__code__,globals(),LocalRuntimeInputs.close.__defaults__)
            phase='PROJECT_BOOTSTRAP'
            bootstrap_actor=prepare_project_bridge(runtime,plan,_compile,_exec)
            def actor_call(operation,args=()):
                return FunctionType(bootstrap_actor[0],bootstrap_actor[1])(bootstrap_actor[2],operation,args)
            bridge=actor_call('import_bridge')
            held=read_file(plan['import_helper']['path'],plan['import_helper']['pin'])
            bs_helper=ModuleType('_saved_F_bootstrap_import_helper_v1')
            vars(bs_helper).update(__file__=plan['import_helper']['path'],_READ_FILE=read_file,_CENSUS_IO=census_io,_PROJECT_BRIDGE=bridge)
            unit=_compile(held,plan['import_helper']['path'],'exec',dont_inherit=True,optimize=0)
            _exec(unit,_vars(bs_helper),_vars(bs_helper));native_bookend()
            expected_bs=validate_import_helper(bs_helper,unit,_native_builtins,census_io,bridge)
            phase='IMPORT_SETUP'

            def spec(name):
                fn=vars(bs_helper.BootstrapImportBoundary)[name];return (FunctionType,fn.__code__,vars(bs_helper),fn.__defaults__)
            runtime.prepare_boundary(spec('_entry'),spec('close'),spec('phase'),spec('profile_raw'),spec('claim_pending'),expected_bs)
            policy=read_file(plan['import_policy']['path'],plan['import_policy']['pin'])
            boundary=bs_helper.open_bootstrap_import_boundary(policy,runtime,expected_bs)
            actor_call('install_guard',(boundary,))
            runtime.handoff_audit();boundary.admit_paths();phase='IMPORT'
            adapter,adapter_bindings,retention=bs_helper.load_bootstrap_adapter(runtime,boundary)
            bs_helper.trace_import_stage(runtime,'before_profile');observed_profile=boundary.profile_raw();bs_helper.trace_import_stage(runtime,'after_profile')
            bs_helper.trace_import_stage(runtime,'before_finish_import')
            construction_result=actor_call('import_returned',(adapter,adapter_bindings,retention,observed_profile))
            observed=runtime._phase;was_live=observed=='LIVE';bs_helper.trace_import_stage(runtime,'after_finish_import')
            if plan['case']=='producer':
                phase='PRODUCER'
                from time import monotonic
                producer_result=actor_call('run',(ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative/draft_01',monotonic()))
            else:phase='PROJECT_REPORT'
    except BaseException as error:
        primary=error;retained=failure_owner(error)
        if retained is not None:runtime=retained
        if isinstance(error,(LocalPreEntryConstructionFailed,LocalPreEntryUnresolved)):resource=getattr(error.owner,'_resource',resource)
    finally:
        if runtime is not None:
            if runtime_close is None:runtime_close=(FunctionType,LocalRuntimeInputs.close.__code__,globals(),LocalRuntimeInputs.close.__defaults__)
            try:bs_helper.trace_import_stage(runtime,'before_final_runtime_close')
            except BaseException as error:secondary.append(error)
            try:
                if bootstrap_actor is not None:
                    actor_call('close',(primary,))
                elif not runtime._cleanup_started:
                    runtime_close[0](runtime_close[1],runtime_close[2],'held_runtime_final_close',runtime_close[3])(runtime,primary)
            except BaseException as error:
                if error is not primary:secondary.append(error)
            try:bs_helper.trace_import_stage(runtime,'after_final_runtime_close')
            except BaseException as error:secondary.append(error)
        if namespace is not None:
            try:ns_close[0](ns_close[1],ns_close[2],'held_old_namespace_close',ns_close[3])(namespace,primary)
            except BaseException as error:secondary.append(error)
        if inputs is not None:
            try:inputs.close()
            except BaseException as error:secondary.append(error)
        if lease is not None:
            try:lease.close()
            except BaseException as error:secondary.append(error)
        if resource is None and inputs is not None:resource=inputs._resource
        if bootstrap_actor is not None:
            try:
                actor_observation=actor_call('observation')
                permission_observation=actor_observation['permission']
            except BaseException as error:secondary.append(error)
        if guard is not None:guard['active']=False
        if _EARLY is not None:_EARLY['active']=False
        try:
            require(not _DLL_DIRECTORY_CLOSE_STATE[0],'directory cookie close already attempted');_DLL_DIRECTORY_CLOSE_STATE[0]=True
            _DLL_DIRECTORY.close();directory_closed=True
        except BaseException as error:secondary.append(error)
    try:namespace_terminal=namespace_terminal_snapshot(runtime,namespace)
    except BaseException as error:secondary.append(error)
    remaining=[48]
    def image(error,depth=0):
        if error is None:return None
        if remaining[0]<=0:return None
        remaining[0]-=1
        if depth>=6:return dict(type=type(error).__name__[:80],message='',primary=None,secondary=[],cause=None,group=[],truncated=True)
        rows=[]
        for item in getattr(error,'secondary',getattr(error,'cleanup',()))[:8]:
            layer,value=item if type(item) is tuple and len(item)==2 else ('cleanup',item)
            rows.append(dict(layer=str(layer)[:80],error=image(value,depth+1)))
        groups=[image(item,depth+1) for item in error.exceptions[:8]] if isinstance(error,native['BaseExceptionGroup']) else []
        return dict(type=type(error).__name__[:80],message=str(error)[:180],primary=image(getattr(error,'primary',None),depth+1),secondary=rows,
            cause=image(error.__cause__,depth+1),group=groups,truncated=remaining[0]<=0)
    success=primary is None and not secondary and directory_closed
    profile=None
    if observed_profile is not None:
        require(len(observed_profile)<=1024**2,'B_S raw metadata cap')
        profile=dict(encoding='zlib_base64',raw_pin=pin(observed_profile),data=_transport_base64.b64encode(_transport_zlib.compress(observed_profile,9)).decode('ascii'))
    report=dict(schema='staged_saved_F_complete_bootstrap_probe_v1',authority='DRAFT_NONAUTHORITATIVE',case=None if plan is None else plan['case'],
        status=('discovery_only' if discovered is not None else 'completed') if success else 'failed',primary=image(primary),secondary=[image(e) for e in secondary],failure_phase=None if primary is None else phase,
        startup_profile=discovered,import_profile=profile,source_epoch=SOURCE_SHA,dll_directory_close_returned=directory_closed,
        runtime_phase_before_close=observed,post_metrics=None if bs_helper is None else bs_helper._POST_METRICS,
        construction_result=construction_result,bootstrap_actor=actor_observation,producer_result=producer_result,namespace_terminal=namespace_terminal,permission_observation=permission_observation,consumer_state=None if runtime is None else runtime._consume_state,
        graph_calls=None if ns_helper is None else ns_helper._GRAPH_STATS['calls'],runtime_was_live=was_live,runtime_phase=None if runtime is None else runtime._phase,resource_phase=None if resource is None else resource.phase,
        self_handles_closed=None if resource is None else not any(resource.pending),close_calls=None if resource is None else resource.close_calls,
        kernel_identity=None if resource is None else resource.observation,source_phase=None if lease is None else lease._phase,
        inputs_phase=None if inputs is None else inputs._phase,namespace_phase=None if namespace is None else namespace._phase,
        runtime_is_resource_owner=runtime is not None and resource is not None and resource.owner is runtime,
        old_inputs_successor_matches=runtime is not None and inputs._successor is runtime,
        old_namespace_successor_matches=runtime is not None and namespace._runtime_peer is runtime,
        boundary_phase=None if runtime is None or runtime._boundary is None else runtime._boundary.phase(),
        boundary_report=None if runtime is None or runtime._boundary is None else json.loads(runtime._boundary.report_raw),
        retained_modules=0 if runtime is None else len(runtime._retention),source_bookends=0 if runtime is None else runtime._source_bookends,
        namespace_alias_absent='experiments.staged_rts24_saved_fresh_adoption_v1' not in sys.modules,
        guard=None if guard is None else {key:guard[key] for key in ('source_open_attempts','protected_open_attempts','write_attempts','process_attempts','faults','sentinel','events')},
        early_audit_blocked=None if _EARLY is None else _EARLY['blocked'],live_at_report=False,**FALSE_GATES)
    encoded=canonical(report);require(len(encoded)<=327680,'complete bootstrap canonical report cap');sys.stdout.buffer.write(encoded+b'\n')
    raise SystemExit(0 if success else 1)

def validate_held_namespace_helper(helper,unit,native,_input_type,_runtime_type,_compile,_exec,_type,_vars):
    namespace_dict=_vars(helper);compiled={c.co_name:c for c in unit.co_consts if _type(c) is CodeType}
    def check_function(function,expected,cls=None):
        require(_type(function) is FunctionType and function.__globals__ is namespace_dict and function.__code__==expected,'held helper compiled binding differs')
        require(function.__kwdefaults__ is None,'held helper keyword defaults differ')
        if expected.co_freevars==('__class__',):require(function.__closure__[0].cell_contents is cls,'held helper class cell differs')
        else:require(function.__closure__ is None,'held helper closure differs')
        defaults=function.__defaults__ or ();names=expected.co_varnames[expected.co_argcount-native['len'](defaults):expected.co_argcount]
        table=dict(_get=native['getattr'],_vars=_vars,_typ=_type,_error=native['BaseException'] if expected.co_qualname=='LiveEntryNamespace.entry' else native['ValueError'],
            _tuple=native['tuple'],_sorted=native['sorted'],_id=native['id'],_getpid=os.getpid,_ident=get_ident,_type=_type,_reject=native['ValueError'],
            _fn=FunctionType,_ctx=namespace_dict,_put=native['object'].__setattr__,_sys=sys,_absent=helper._ABSENT,_any=native['any'],
            _failure_type=helper.NamespaceConstructionFailed,_base=native['BaseException'],_input_type=_input_type,_runtime_type=_runtime_type,_compile=_compile,
            _module_type=_type(sys),_exec=_exec,_require=helper.require,_owner_type=helper.LiveEntryNamespace,_graph_type=helper.NamespaceGraph,
            _tuple_type=native['tuple'],_class=helper.NamespaceConstructionFailed,_new=native['RuntimeError'].__new__,_init=native['RuntimeError'].__init__,
            _getdict=native['object'].__getattribute__,_bind_code=compiled['verify_helper_bindings'],_check_code=compiled['verify_helper_bindings'],
            _verify_code=compiled['verify_namespace'],_code=compiled['timed_namespace_graph'] if expected.co_qualname=='NamespaceGraph.freeze' else compiled['verify_runtime_namespace'] if expected.co_name=='close_runtime_namespace' else compiled['verify_namespace'],_failure_code=compiled['make_namespace_failure'],
            _defs=helper.verify_runtime_namespace.__defaults__ if expected.co_name=='close_runtime_namespace' else helper.timed_namespace_graph.__defaults__ if expected.co_qualname=='NamespaceGraph.freeze' else helper.verify_namespace.__defaults__ if expected.co_qualname in ('LiveEntryNamespace.entry','LiveEntryNamespace.close') else helper.verify_helper_bindings.__defaults__,
            _verify_defs=helper.verify_namespace.__defaults__,_failure_defs=helper.make_namespace_failure.__defaults__,
                    _len=native['len'],_all=native['all'],_zip=native['zip'],_path=native['str'](ROOT/ENTRY),_bool=native['bool'],_check_defs=helper.verify_helper_bindings.__defaults__,
            _image_code=compiled['runtime_namespace_image'] if expected.co_name=='verify_runtime_namespace' else compiled['owner_image'],_image_defs=helper.runtime_namespace_image.__defaults__ if expected.co_name=='verify_runtime_namespace' else helper.owner_image.__defaults__,
            _graph_builder_code=compiled['timed_namespace_graph'],_graph_builder_defs=helper.timed_namespace_graph.__defaults__,
            _reader_code=compiled['freeze_namespace_graph'],_reader_defs=helper.freeze_namespace_graph.__defaults__,
            _stats=helper._GRAPH_STATS,_clock=helper._TRACE_CLOCK,_write=helper._TRACE_WRITE,_flush=helper._TRACE_FLUSH,_dumps=helper._TRACE_DUMPS)
        graph_roots=(native['type'],native['id'],native['len'],native['tuple'],native['dict'],native['list'],native['Ellipsis'],native['bytes'],native['str'],native['int'],native['float'],native['bool'],native['complex'],native['set'],native['frozenset'],native['staticmethod'],native['classmethod'],native['property'],native['sorted'],native['any'],native['ValueError'],
            _type(sys),FunctionType,CodeType,helper.CellType,helper.MappingProxyType,helper.GetSetDescriptorType,helper.MemberDescriptorType,native['vars'],helper.dataclasses.Field,helper.dataclasses._DataclassParams,helper.dataclasses.InitVar,helper._PATH_TYPE,helper._EXTERNAL_VALUE_TYPES,helper._SENTINELS,helper.json.dumps,helper.sha256,native['object'].__getattribute__)
        for name,value in native['zip'](names,defaults):
            if name=='_roots':require(_type(value) is native['tuple'] and native['len'](value)==native['len'](graph_roots) and native['all'](a is b for a,b in native['zip'](value,graph_roots)),'held graph reader roots differ')
            elif name=='_path':require(_type(value) is native['str'] and value==table['_path'],'held helper path default differs')
            else:require(value is None if name=='primary' else _type(value) is native['int'] and value==0 if name=='depth' else name in table and (value==table[name] if _type(value) is CodeType else value is table[name]),'held helper default differs: '+name)
    for name,expected in compiled.items():
        if name.startswith('<'):continue
        value=namespace_dict[name]
        if name in ('NamespaceGraph','NamespaceConstructionFailed','LiveEntryNamespace'):
            require(_type(value) is native['type'] and value.__module__==helper.__name__,'held helper class differs')
            for method in expected.co_consts:
                if _type(method) is CodeType and not method.co_name.startswith('<'):
                    member=_vars(value)[method.co_name]
                    if _type(member) is native['staticmethod']:member=member.__func__
                    check_function(member,method,value)
        else:check_function(value,expected)




def prepare_project_bridge(runtime,plan,native_compile,native_exec):
    require(native_compile is builtins.compile and native_exec is builtins.exec,'held native source evaluator required')
    require(type(runtime) is LocalRuntimeInputs and runtime._phase=='ADOPTED','same pre-import creating runtime required')
    require(check_plan(runtime._raw)==plan,'same checked construction manifest required')
    runtime.entry()
    ref=plan['producer_helpers']['bootstrap_loader'];raw=read_file(ref['path'],ref['pin'])
    context={name:globals()[name] for name in ('builtins','LocalRuntimeInputs','check_plan','read_file','pin','decode',
        'FunctionType','CodeType','producer_helper_paths','require')}
    context.update(__file__=ref['path'],__name__='_saved_F_held_project_loader',__builtins__=vars(builtins))
    unit=native_compile(raw,ref['path'],'exec',dont_inherit=True,optimize=0);native_exec(unit,context,context)
    codes=[code for code in unit.co_consts if type(code) is CodeType and code.co_name==code.co_qualname=='prepare_project_bridge']
    require(len(codes)==1,'single source-held project loader required')
    function=context['prepare_project_bridge']
    require(type(function) is FunctionType and function.__code__==codes[0] and function.__globals__ is context
        and function.__defaults__ is function.__kwdefaults__ is function.__closure__ is None,'original project loader metadata required')
    return FunctionType(codes[0],context)(runtime,plan,native_compile,native_exec)




def namespace_terminal_snapshot(owner,expected_namespace):
    """Observe retained ownership data after close; no entry or filesystem read."""
    if owner is None:return None
    namespace=expected_namespace;resource=owner._resource;inputs=namespace._inputs;registry=namespace._modules
    require(type(registry) is dict and len(registry)<=4096 and all(type(key) is str for key in registry),
        'bounded original namespace registry required')
    actual,reference=namespace._aliases
    expected=('experiments.staged_rts24_saved_fresh_adoption_v1','_saved_F_entry_reference_v1')
    require((actual,reference)==expected,'original namespace aliases required')
    return dict(schema='staged_saved_F_namespace_terminal_observation_v1',authority='DRAFT_NONAUTHORITATIVE',
        runtime_phase=owner._phase,cleanup_started=owner._cleanup_started,failure_absent=owner._failure is None,
        resource_phase=resource.phase,resource_owner_same=resource.owner is owner,pending=[bool(value) for value in resource.pending],
        namespace_phase=namespace._phase,namespace_same=owner._namespace is namespace,peer_same=namespace._runtime_peer is owner,
        source_same=owner._source is inputs,inputs_phase=inputs._phase,successor_same=inputs._successor is owner,
        resource_same=inputs._resource is resource,registry_same=registry is sys.modules,
        reference_registered=namespace._reference_registered,actual_key_absent=actual not in registry,
        reference_key_absent=reference not in registry,
        actual_aliases=sorted(key for key,value in tuple(registry.items()) if value is namespace.module),
        reference_aliases=sorted(key for key,value in tuple(registry.items()) if value is namespace.reference))


def require_namespace_terminal(value,success):
    require(type(value) is dict and value['schema']=='staged_saved_F_namespace_terminal_observation_v1'
        and value['authority']=='DRAFT_NONAUTHORITATIVE','original namespace terminal observation required')
    require(value['resource_phase']=='CLOSED' and value['namespace_phase']==value['inputs_phase']=='CONSUMED',
        'closed runtime/resource and transferred namespace required')
    if success:require(value['runtime_phase']=='CLOSED' and value['failure_absent'] is True,'successful runtime close required')
    else:require(value['runtime_phase'] in ('CLOSED','UNRESOLVED')
        and value['failure_absent'] is (value['runtime_phase']=='CLOSED'),'retained runtime failure state required')
    for key in ('cleanup_started','resource_owner_same','namespace_same','peer_same','source_same',
            'successor_same','resource_same','registry_same','actual_key_absent','reference_key_absent'):
        require(value[key] is True,'namespace terminal invariant failed: '+key)
    require(value['reference_registered'] is False and value['pending']==[False,False]
        and all(type(item) is bool for item in value['pending'])
        and value['actual_aliases']==value['reference_aliases']==[],'namespace aliases or native handles remain')
    return value


if __name__=='__main__':_probe_main()
