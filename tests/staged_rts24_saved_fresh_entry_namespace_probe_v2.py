"""Appended only to the held v4 bootstrap; executes ENTRY initialization only."""
def namespace_failure_owner(helper,error,_vars=vars,_type=type,_isinstance=isinstance,_module_type=type(sys)):
    if helper is None:return None
    if _type(helper) is not _module_type:return None
    kind=_vars(helper).get('NamespaceConstructionFailed')
    return error.owner if _type(kind) is _type and _isinstance(error,kind) else None

def validate_held_namespace_helper(helper,unit,native,_input_type,_compile,_exec,_type,_vars):
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
            _failure_type=helper.NamespaceConstructionFailed,_base=native['BaseException'],_input_type=_input_type,_compile=_compile,
            _module_type=_type(sys),_exec=_exec,_require=helper.require,_owner_type=helper.LiveEntryNamespace,_graph_type=helper.NamespaceGraph,
            _tuple_type=native['tuple'],_class=helper.NamespaceConstructionFailed,_new=native['RuntimeError'].__new__,_init=native['RuntimeError'].__init__,
            _getdict=native['object'].__getattribute__,_bind_code=compiled['verify_helper_bindings'],_check_code=compiled['verify_helper_bindings'],
            _verify_code=compiled['verify_namespace'],_code=compiled['freeze_namespace_graph'] if expected.co_qualname=='NamespaceGraph.freeze' else compiled['verify_namespace'],_failure_code=compiled['make_namespace_failure'],
            _defs=helper.freeze_namespace_graph.__defaults__ if expected.co_qualname=='NamespaceGraph.freeze' else helper.verify_namespace.__defaults__ if expected.co_qualname in ('LiveEntryNamespace.entry','LiveEntryNamespace.close') else helper.verify_helper_bindings.__defaults__,
            _verify_defs=helper.verify_namespace.__defaults__,_failure_defs=helper.make_namespace_failure.__defaults__,
                    _len=native['len'],_all=native['all'],_zip=native['zip'],_path=native['str'](ROOT/ENTRY),_bool=native['bool'],_check_defs=helper.verify_helper_bindings.__defaults__,
            _image_code=compiled['owner_image'],_image_defs=helper.owner_image.__defaults__,
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

def _probe_main(_compile=compile,_exec=exec,_type=type,_vars=vars,_native_builtins=tuple(vars(builtins).items())):
    native={key:value for key,value in _native_builtins}
    plan=guard=lease=inputs=namespace=helper=resource=ns_entry=ns_close=None;primary=None;secondary=[];phase='MANIFEST';directory_closed=False
    try:
        path=Path(sys.argv[2]);out=ROOT/'results/tables/staged_rts24_saved_fresh_entry_namespace_startup_repair_v1_non_authoritative'
        require(path.parent==out and path.name.startswith('probe_') and path.name.endswith('.plan.json'),'fixed namespace manifest location')
        raw=read_file(path,dict(bytes=path.lstat().st_size,sha256=sys.argv[3]));plan=check_plan(raw)
        require(path.name=='probe_'+plan['case']+'.plan.json','manifest case differs')
        if plan['case']=='discovery':discovered=startup_profile(plan)
        else:
            discovered=None;guard=install_guard(plan);phase='SELF';lease=open_local_pre_entry_lease(raw,guard)
            resource=lease._resource;inputs=lease.transfer();phase='NAMESPACE'
            helper_raw=read_file(plan['namespace_helper']['path'],plan['namespace_helper']['pin'])
            require(len(helper_raw)<=131072,'namespace helper cap')
            inputs.entry()
            def native_bookend():
                current=_vars(builtins)
                require(native['len'](current)==native['len'](native),'bootstrap builtin keys changed')
                for key,value in native.items():require(current.get(key) is value,'bootstrap builtin changed')
            native_bookend()
            from types import ModuleType
            helper=ModuleType('_saved_F_namespace_helper_v1')
            helper.__dict__.update(_INPUT_TYPE=LocalPreEntryInputs,__file__=plan['namespace_helper']['path'])
            if plan['case']=='helper_init_failure':raise ValueError('injected_helper_initialization_failure')
            unit=_compile(helper_raw,plan['namespace_helper']['path'],'exec',dont_inherit=True,optimize=0)
            _exec(unit,_vars(helper),_vars(helper));native_bookend()
            validate_held_namespace_helper(helper,unit,native,LocalPreEntryInputs,_compile,_exec,_type,_vars)
            native_bookend();held_bindings=helper.capture_helper_bindings()
            ns_entry=(FunctionType,helper.LiveEntryNamespace.entry.__code__,vars(helper),helper.LiveEntryNamespace.entry.__defaults__)
            ns_close=(FunctionType,helper.LiveEntryNamespace.close.__code__,vars(helper),helper.LiveEntryNamespace.close.__defaults__)
            def observer(event,args):
                if plan['case']=='partial_namespace' and event=='electricity_grid.namespace.registered':raise ValueError('injected_after_namespace_registration')
            sys.addaudithook(observer)
            namespace=helper.open_entry_namespace(inputs,held_bindings)
            if plan['case']=='global_rebind':namespace.module.require=lambda *args,**kwargs:None
            if plan['case']=='alias_replace':sys.modules[helper.ACTUAL_NAME]=ModuleType('foreign_namespace')
            ns_entry[0](ns_entry[1],ns_entry[2],'held_namespace_entry',ns_entry[3])(namespace)
    except BaseException as error:
        primary=error
        retained=namespace_failure_owner(helper,error)
        if retained is not None:namespace=retained
        if isinstance(error,(LocalPreEntryConstructionFailed,LocalPreEntryUnresolved)):resource=getattr(error.owner,'_resource',resource)
    finally:
        if namespace is not None:
            try:ns_close[0](ns_close[1],ns_close[2],'held_namespace_cleanup',ns_close[3])(namespace)
            except BaseException as error:
                if error is not primary:secondary.append(error)
        if inputs is not None:
            try:inputs.close()
            except BaseException as error:secondary.append(error)
        elif resource is not None:
            try:resource.owner.close()
            except BaseException as error:secondary.append(error)
        if lease is not None:
            try:lease.close()
            except BaseException as error:secondary.append(error)
        if guard is not None:guard['active']=False
        if _EARLY is not None:_EARLY['active']=False
        try:
            require(not _DLL_DIRECTORY_CLOSE_STATE[0],'cookie close already attempted');_DLL_DIRECTORY_CLOSE_STATE[0]=True
            _DLL_DIRECTORY.close();directory_closed=True
        except BaseException as error:secondary.append(error)
    def image(error,depth=0):
        if error is None:return None
        if depth>=5:return dict(type=type(error).__name__,message='',primary=None,secondary=[],truncated=True)
        rows=[]
        for item in getattr(error,'secondary',()):
            layer,value=item if type(item) is tuple and len(item)==2 else ('cleanup',item)
            rows.append(dict(layer=layer,error=image(value,depth+1)))
        return dict(type=type(error).__name__,message=str(error)[:160],primary=image(getattr(error,'primary',None),depth+1),secondary=rows,truncated=False)
    discovered=locals().get('discovered');success=primary is None and not secondary and directory_closed
    active_alias=sys.modules.get('experiments.staged_rts24_saved_fresh_adoption_v1')
    report=dict(schema='staged_saved_F_entry_namespace_probe_v2',authority='DRAFT_NONAUTHORITATIVE',
        case=None if plan is None else plan['case'],status=('discovery_only' if discovered is not None else 'completed') if success else 'failed',
        primary=image(primary),secondary=[image(e) for e in secondary],failure_phase=None if primary is None else phase,
        startup_profile=discovered,dll_directory_close_returned=directory_closed,source_epoch=SOURCE_SHA,
        self_handles_closed=None if resource is None else not any(resource.pending),close_calls=None if resource is None else resource.close_calls,
        kernel_identity=None if resource is None else resource.observation,source_phase=None if lease is None else lease._phase,
        inputs_phase=None if inputs is None else inputs._phase,namespace_phase=None if namespace is None else namespace._phase,
        namespace_nodes=0 if namespace is None or not hasattr(namespace,'_objects') else len(namespace._objects),
        actual_namespace_initialized=namespace is not None and namespace._actual_initialized,
        entry_namespace_executed=namespace is not None and namespace._exec_attempts>0,
        entry_exec_attempts=0 if namespace is None else namespace._exec_attempts,
        entry_exec_completed=0 if namespace is None else namespace._exec_completed,
        reference_alias_absent='_saved_F_entry_reference_v1' not in sys.modules,
        actual_alias_absent=active_alias is None,foreign_alias_retained=active_alias is not None and (namespace is None or active_alias is not namespace.module),
        actual_module_was_main=False,live_at_report=False,adapter_imported=any(n=='src' or n.startswith('src.') for n in sys.modules),
        guard=None if guard is None else {k:guard[k] for k in ('source_open_attempts','protected_open_attempts','write_attempts','process_attempts','faults','sentinel','events')},
        early_audit_blocked=None if _EARLY is None else _EARLY['blocked'],**FALSE_GATES)
    encoded=canonical(report);require(len(encoded)<=131072,'namespace report cap');sys.stdout.buffer.write(encoded+b'\n')
    raise SystemExit(0 if success else 1)

if __name__=='__main__':_probe_main()
