"""Pinned bootstrap loader; no P1 admission is issued here."""


def prepare_project_bridge(runtime,plan,native_compile,native_exec):
    # The ADOPTED bootstrap authenticates this external helper's pinned raw/code.
    require(native_compile is builtins.compile and native_exec is builtins.exec,'held native source evaluator required')
    require(type(runtime) is LocalRuntimeInputs and runtime._phase=='ADOPTED','same pre-import creating runtime required')
    require(check_plan(runtime._raw)==plan,'same checked construction manifest required')
    runtime.entry();runtime.source_bookend()
    refs=plan['producer_helpers'];paths=producer_helper_paths()
    require(set(refs)==set(paths),'complete producer helper set required')
    held={key:read_file(refs[key]['path'],refs[key]['pin']) for key in paths}
    require(pin(held['predecessor_checkpoint'])['sha256']=='bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de',
        'original NFC12 checkpoint required')
    predecessor=decode(held['predecessor_checkpoint'])
    require(pin(held['predecessor_registration'])==predecessor['root_map_before_checkpoint']['registration.json'],
        'checkpoint-bound complete registration required')
    from types import ModuleType
    modules={};units={}
    for key in ('utilities','lifecycle','project_graph','construction','capture'):
        module=ModuleType('_saved_F_project_'+key)
        extra=dict(_RUNTIME_TYPE=LocalRuntimeInputs) if key=='construction' else {}
        vars(module).update(__file__=refs[key]['path'],**extra)
        unit=native_compile(held[key],refs[key]['path'],'exec',dont_inherit=True,optimize=0)
        native_exec(unit,vars(module),vars(module));modules[key]=module;units[key]=unit
    def function_code(key,name):
        codes=[code for code in units[key].co_consts if type(code) is CodeType and code.co_name==code.co_qualname==name]
        require(len(codes)==1,'unique held source function required');return codes[0]
    utility=vars(modules['utilities'])
    witness=FunctionType(function_code('utilities','_program_witness'),utility)
    witnesses=tuple(witness(vars(modules[key]),held[key]) for key in ('utilities','lifecycle','project_graph','construction','capture'))
    isolated=dict(__builtins__=dict(vars(builtins)),FunctionType=FunctionType)
    verify=FunctionType(function_code('utilities','_verify_programs'),isolated)
    verify(witnesses,function_code('utilities','_metadata'))
    code,contract=FunctionType(function_code('capture','current'),vars(modules['capture']))()
    require(contract['source_contract']['checkpoint_pin']==pin(held['predecessor_checkpoint'])
        and contract['source_contract']['registration_pin']==pin(held['predecessor_registration']),
        'held prebound derivation provenance differs')
    source_program=FunctionType(function_code('construction','source_program'),vars(modules['construction']))
    program=source_program(held['construction'],dict(_RUNTIME_TYPE=LocalRuntimeInputs),held['utilities'])
    bridge=FunctionType(program[0],program[1])(program[2],'new_import_bridge',
        (runtime,modules['project_graph'],held['project_graph'],modules['lifecycle'],held['lifecycle'],code,None),{})
    verify(witnesses,function_code('utilities','_metadata'))
    runtime.entry();runtime.source_bookend()
    return bridge
