"""Held bootstrap coordinator for local ownership and import-only diagnostics."""
def failure_owner(error):
    owner=getattr(error,'owner',None)
    return owner if type(owner) is LocalRuntimeInputs else None

def validate_import_helper(helper,unit):
    namespace=vars(helper)
    classes={'BootstrapImportRejected','_SavedImportCPUQueryDenied','_SavedImportFrameMarker','BootstrapImportUnresolved','BootstrapImportBoundary'}
    def check(fn,code,cls=None):
        require(type(fn) is FunctionType and fn.__globals__ is namespace and fn.__code__==code,'B_S source callable differs')
        require(fn.__defaults__ is None or fn.__defaults__==(None,),'B_S source defaults differ')
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

def _probe_main(_compile=compile,_exec=exec,_type=type,_vars=vars,_native_builtins=tuple(vars(builtins).items())):
    native={key:value for key,value in _native_builtins}
    plan=guard=lease=inputs=namespace=ns_helper=bs_helper=runtime=boundary=resource=None
    primary=None;secondary=[];phase='MANIFEST';discovered=None;directory_closed=False;observed_profile=None;was_live=False
    ns_close=runtime_close=None
    try:
        out=ROOT/'results/tables/staged_rts24_saved_fresh_runtime_handoff_v1_non_authoritative';path=Path(sys.argv[2])
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
            ns_helper,unit=helper_load(plan['namespace_helper'],'_saved_F_namespace_helper_v2',dict(_INPUT_TYPE=LocalPreEntryInputs,_RUNTIME_TYPE=LocalRuntimeInputs))
            validate_held_namespace_helper(ns_helper,unit,native,LocalPreEntryInputs,LocalRuntimeInputs,_compile,_exec,_type,_vars)
            bindings=ns_helper.capture_helper_bindings();namespace=ns_helper.open_entry_namespace(inputs,bindings)
            ns_close=(FunctionType,ns_helper.LiveEntryNamespace.close.__code__,vars(ns_helper),ns_helper.LiveEntryNamespace.close.__defaults__)
            bs_helper,unit=helper_load(plan['import_helper'],'_saved_F_bootstrap_import_helper_v1',dict(_READ_FILE=read_file))
            validate_import_helper(bs_helper,unit)
            def observer(event,args):
                case=plan['case']
                if event=='electricity_grid.runtime.transfer_prepared' and case=='precommit':raise ValueError('injected_runtime_precommit')
                if event=='electricity_grid.runtime.owner_committed' and case=='postcommit':raise ValueError('injected_runtime_postcommit')
                if event=='sys.addaudithook' and case=='blocked_installation' and runtime is not None and runtime._boundary is not None:raise RuntimeError('injected_B_S_installation_block')
                if event=='electricity_grid.runtime.audit_handoff_between' and case=='handoff_middle':raise ValueError('injected_runtime_audit_handoff_middle')
                if event=='electricity_grid.B_S.finder_stage' and (case=='M_only' and args[0]==1 or case=='after_D' and args[0]==2):raise ValueError('injected_B_S_finder_stage_'+str(args[0]))
            sys.addaudithook(observer);phase='TRANSFER'
            runtime=namespace.transfer_runtime();runtime_close=(FunctionType,LocalRuntimeInputs.close.__code__,globals(),LocalRuntimeInputs.close.__defaults__)
            phase='IMPORT_SETUP'
            def spec(name):
                fn=vars(bs_helper.BootstrapImportBoundary)[name];return (FunctionType,fn.__code__,vars(bs_helper),fn.__defaults__)
            runtime.prepare_boundary(spec('_entry'),spec('close'),spec('phase'),spec('profile_raw'),spec('claim_pending'))
            policy=read_file(plan['import_policy']['path'],plan['import_policy']['pin'])
            boundary=bs_helper.open_bootstrap_import_boundary(policy,runtime)
            runtime.handoff_audit();boundary.admit_paths();phase='IMPORT'
            adapter,adapter_bindings,retention=bs_helper.load_bootstrap_adapter(runtime,boundary)
            observed_profile=boundary.profile_raw();runtime.finish_import(adapter,adapter_bindings,retention)
            runtime.entry();was_live=runtime._phase=='LIVE'
    except BaseException as error:
        primary=error;retained=failure_owner(error)
        if retained is not None:runtime=retained
        if isinstance(error,(LocalPreEntryConstructionFailed,LocalPreEntryUnresolved)):resource=getattr(error.owner,'_resource',resource)
    finally:
        if runtime is not None:
            if runtime_close is None:runtime_close=(FunctionType,LocalRuntimeInputs.close.__code__,globals(),LocalRuntimeInputs.close.__defaults__)
            try:runtime_close[0](runtime_close[1],runtime_close[2],'held_runtime_final_close',runtime_close[3])(runtime,primary)
            except BaseException as error:
                if error is not primary:secondary.append(error)
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
        if guard is not None:guard['active']=False
        if _EARLY is not None:_EARLY['active']=False
        try:
            require(not _DLL_DIRECTORY_CLOSE_STATE[0],'directory cookie close already attempted');_DLL_DIRECTORY_CLOSE_STATE[0]=True
            _DLL_DIRECTORY.close();directory_closed=True
        except BaseException as error:secondary.append(error)
    remaining=[48]
    def image(error,depth=0):
        if error is None:return None
        if depth>=6 or remaining[0]<=0:return dict(type=type(error).__name__,message='',primary=None,secondary=[],truncated=True)
        remaining[0]-=1;rows=[]
        for item in getattr(error,'secondary',getattr(error,'cleanup',())):
            layer,value=item if type(item) is tuple and len(item)==2 else ('cleanup',item)
            rows.append(dict(layer=layer,error=image(value,depth+1)))
        return dict(type=type(error).__name__,message=str(error)[:180],primary=image(getattr(error,'primary',None),depth+1),secondary=rows,truncated=False)
    success=primary is None and not secondary and directory_closed
    profile=None
    if observed_profile is not None:
        require(len(observed_profile)<=1024**2,'B_S raw metadata cap')
        profile=dict(encoding='zlib_base64',raw_pin=pin(observed_profile),data=_transport_base64.b64encode(_transport_zlib.compress(observed_profile,9)).decode('ascii'))
    report=dict(schema='staged_saved_F_runtime_handoff_probe_v1',authority='DRAFT_NONAUTHORITATIVE',case=None if plan is None else plan['case'],
        status=('discovery_only' if discovered is not None else 'completed') if success else 'failed',primary=image(primary),secondary=[image(e) for e in secondary],failure_phase=None if primary is None else phase,
        startup_profile=discovered,import_profile=profile,source_epoch=SOURCE_SHA,dll_directory_close_returned=directory_closed,
        runtime_was_live=was_live,runtime_phase=None if runtime is None else runtime._phase,resource_phase=None if resource is None else resource.phase,
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
    encoded=canonical(report);require(len(encoded)<=131072,'runtime diagnostic report cap');sys.stdout.buffer.write(encoded+b'\n')
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
            _verify_code=compiled['verify_namespace'],_code=compiled['freeze_namespace_graph'] if expected.co_qualname=='NamespaceGraph.freeze' else compiled['verify_runtime_namespace'] if expected.co_name=='close_runtime_namespace' else compiled['verify_namespace'],_failure_code=compiled['make_namespace_failure'],
            _defs=helper.verify_runtime_namespace.__defaults__ if expected.co_name=='close_runtime_namespace' else helper.freeze_namespace_graph.__defaults__ if expected.co_qualname=='NamespaceGraph.freeze' else helper.verify_namespace.__defaults__ if expected.co_qualname in ('LiveEntryNamespace.entry','LiveEntryNamespace.close') else helper.verify_helper_bindings.__defaults__,
            _verify_defs=helper.verify_namespace.__defaults__,_failure_defs=helper.make_namespace_failure.__defaults__,
                    _len=native['len'],_all=native['all'],_zip=native['zip'],_path=native['str'](ROOT/ENTRY),_bool=native['bool'],_check_defs=helper.verify_helper_bindings.__defaults__,
            _image_code=compiled['runtime_namespace_image'] if expected.co_name=='verify_runtime_namespace' else compiled['owner_image'],_image_defs=helper.runtime_namespace_image.__defaults__ if expected.co_name=='verify_runtime_namespace' else helper.owner_image.__defaults__,
            _graph_builder_code=compiled['freeze_namespace_graph'],_graph_builder_defs=helper.freeze_namespace_graph.__defaults__)
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


if __name__=='__main__':_probe_main()
