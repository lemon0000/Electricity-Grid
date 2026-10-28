"""Compile-only successor construction; no launch, grant or Source49 execution."""
from hashlib import sha256
from pathlib import Path

ROOT=Path(__file__).absolute().parents[1]
OUT='staged_rts24_saved_fresh_project_construction_v1_non_authoritative'
PAIRS=(
    ('core','experiments/staged_rts24_saved_fresh_pre_entry_lease_v39.py','experiments/staged_rts24_saved_fresh_pre_entry_lease_v40.py'),
    ('probe','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v37.py','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v38.py'),
    ('parent','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v36.py','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v37.py'))


def replace(source,before,after,count=1):
    assert source.count(before)==count,(before,source.count(before),count)
    return source.replace(before,after)


PATHS_FUNCTION='''

def producer_helper_paths():
    return dict(bootstrap_loader=str(ROOT/'experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v1.py'),
        construction=str(ROOT/'experiments/staged_rts24_saved_fresh_producer_bootstrap_v3.py'),
        project_graph=str(ROOT/'experiments/staged_rts24_saved_fresh_producer_project_graph_v3.py'),
        lifecycle=str(ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v2.py'),
        utilities=str(ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v1.py'),
        capture=str(ROOT/'experiments/staged_rts24_saved_fresh_prebound_expectation_code_v3.py'),
        predecessor_checkpoint=str(ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v12_non_authoritative/checkpoint.json'),
        predecessor_registration=str(ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v12_non_authoritative/registration.json'))


def check_producer_helpers(plan):
    paths=producer_helper_paths();refs=plan['producer_helpers']
    require(type(refs) is dict and set(refs)==set(paths),'closed producer helper references')
    for key,path in paths.items():
        ref=refs[key]
        require(type(ref) is dict and set(ref)=={'path','pin'} and ref['path']==path,'fixed producer helper path')
        value=ref['pin']
        require(type(value) is dict and set(value)=={'bytes','sha256'} and type(value['bytes']) is int
            and 0<value['bytes']<=1048576 and type(value['sha256']) is str and len(value['sha256'])==64
            and all(c in '0123456789abcdef' for c in value['sha256']),'closed producer helper pin')
    require(plan['import_helper']['path']==str(ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v4.py'),
        'construction B_S source required')
'''


LOADER_FUNCTION='''

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
'''

LOADER_PATH='experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v1.py'
LOADER_WRAPPER='''

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
'''


def loader_source():return ('"""Pinned bootstrap loader; no P1 admission is issued here."""\n'+LOADER_FUNCTION).encode('utf8')


def core(source):
    source=replace(source,'staged_rts24_saved_fresh_nfc_v12_non_authoritative',OUT,3)
    source=replace(source,"import_policy import_profile case'","import_policy import_profile producer_helpers case'")
    source=replace(source,"plan['schema']=='staged_saved_F_runtime_handoff_manifest_v1'",
        "plan['schema']=='staged_saved_F_project_construction_manifest_v1'")
    source=replace(source,"plan['case'] in ('discovery','import_discovery','normal','precommit','postcommit','blocked_installation','handoff_middle','M_only','after_D')",
        "plan['case'] in ('discovery','import_discovery')")
    source=replace(source,"    return plan\n\n\ndef read_file","    check_producer_helpers(plan);return plan\n\n\ndef read_file")
    # Appending definitions preserves all existing Core class/method line tables.
    return (source+PATHS_FUNCTION).encode('utf8')


def probe(source):
    source=replace(source,'staged_rts24_saved_fresh_nfc_v12_non_authoritative',OUT)
    source=replace(source,"schema='staged_saved_F_runtime_handoff_probe_v2'","schema='staged_saved_F_project_construction_probe_v1'")
    source=replace(source,'def validate_import_helper(helper,unit,native_builtins,census_io):',
        'def validate_import_helper(helper,unit,native_builtins,census_io,held_bridge):')
    source=replace(source,"    namespace=vars(helper);require(namespace['__builtins__'] is current,'original B_S builtins dict required')",
        "    namespace=vars(helper);require(namespace['__builtins__'] is current,'original B_S builtins dict required')\n    require(type(held_bridge) is tuple and len(held_bridge)==3 and namespace.get('_PROJECT_BRIDGE') is held_bridge,'original held project bridge required')")
    source=replace(source,"        elif code.co_name=='_observe_machinery':",'''        elif code.co_name=='project_bridge_call':expected=(FunctionType,type,len,ValueError,tuple)
        elif code.co_name=='load_bootstrap_adapter':
            expected=(namespace['verify_bootstrap_import_bindings'].__code__,namespace['verify_bootstrap_import_bindings'].__defaults__,FunctionType,namespace,
                namespace['project_bridge_call'].__code__,namespace['project_bridge_call'].__defaults__,held_bridge)
        elif code.co_name=='_observe_machinery':''')
    source=replace(source,"namespace['_POST_METRICS'],(dict,native['int'],native['bool']),ValueError)",
        "namespace['_POST_METRICS'],(dict,native['int'],native['bool']),ValueError,FunctionType,namespace['project_bridge_call'].__code__,namespace['project_bridge_call'].__defaults__,held_bridge)")
    source=replace(source,"('open_bootstrap_import_boundary','load_bootstrap_adapter')","('open_bootstrap_import_boundary',)")
    source=replace(source,"            bs_helper,unit=helper_load(plan['import_helper'],'_saved_F_bootstrap_import_helper_v1',dict(_READ_FILE=read_file,_CENSUS_IO=census_io))\n            expected_bs=validate_import_helper(bs_helper,unit,_native_builtins,census_io)\n",'')
    source=replace(source,"            phase='IMPORT_SETUP'",'''            phase='PROJECT_BOOTSTRAP'
            bridge=prepare_project_bridge(runtime,plan,_compile,_exec)
            held=read_file(plan['import_helper']['path'],plan['import_helper']['pin'])
            bs_helper=ModuleType('_saved_F_bootstrap_import_helper_v1')
            vars(bs_helper).update(__file__=plan['import_helper']['path'],_READ_FILE=read_file,_CENSUS_IO=census_io,_PROJECT_BRIDGE=bridge)
            unit=_compile(held,plan['import_helper']['path'],'exec',dont_inherit=True,optimize=0)
            _exec(unit,_vars(bs_helper),_vars(bs_helper));native_bookend()
            expected_bs=validate_import_helper(bs_helper,unit,_native_builtins,census_io,bridge)
            phase='IMPORT_SETUP'
''')
    source=replace(source,"            phase='CONSUMER_PREPARATION';runtime.prepare_consumer()\n",'')
    source=replace(source,"            phase='CONSUMER';consumer_result=runtime.consume_once('expectation_binding',b'{\"consumer\":\"expectation_binding\",\"v\":1}')",'''            phase='PROJECT_REPORT'
            bundle=FunctionType(bridge[0],bridge[1])(bridge[2],'bundle',runtime,())
            require(bundle[2][3][2][0]['_P1_AUTHORITY'] is None,'construction must remain unadmitted')
            construction_result=FunctionType(bridge[0],bridge[1])(bridge[2],'report',runtime,())''')
    source=replace(source,'observed=None;consumer_result=None','observed=None;construction_result=None')
    source=replace(source,"        consumer_result=None if consumer_result is None else json.loads(consumer_result),consumer_state=None if runtime is None else runtime._consume_state,",
        "        construction_result=construction_result,consumer_state=None if runtime is None else runtime._consume_state,")
    source=replace(source,"if __name__=='__main__':_probe_main()",LOADER_WRAPPER+"\n\nif __name__=='__main__':_probe_main()")
    return source.encode('utf8')


def parent(source):
    source=replace(source,'staged_rts24_saved_fresh_nfc_v12_non_authoritative',OUT)
    source=replace(source,'lease_v39.py','lease_v40.py')
    source=replace(source,'probe_v37.py','probe_v38.py')
    source=replace(source,'staged_rts24_saved_fresh_xz_transport_v1.py','staged_rts24_saved_fresh_utf16_transport_v1.py')
    source=replace(source,"def manifest(case,code):","def manifest(case,code):\n    assert case in ('discovery','import_discovery'),'construction diagnostic only; no producer admission'")
    source=replace(source,"schema='staged_saved_F_runtime_handoff_manifest_v1'","schema='staged_saved_F_project_construction_manifest_v1'")
    source=replace(source,'staged_rts24_saved_fresh_bootstrap_post_return_v2.py','staged_rts24_saved_fresh_bootstrap_post_return_v4.py',3)
    source=replace(source,'import_profile=import_profile,case=case)',
        "import_profile=import_profile,producer_helpers=producer_references(),case=case)")
    source=replace(source,"plan['case'] in ('discovery','normal')","plan['case'] in ('discovery','import_discovery')")
    source=replace(source,"    if plan['case']=='normal':\n        assert plan['startup_profile']==dict(path=str(OUT/'startup_profile.json'),pin=pin((OUT/'startup_profile.json').read_bytes()))\n        assert plan['import_profile']==REFERENCE.reference()['reference']\n    else:assert plan['startup_profile'] is plan['import_profile'] is None",'''    assert plan['producer_helpers']==producer_references()
    for ref in plan['producer_helpers'].values():core.read_file(ref['path'],ref['pin'])
    if plan['case']=='import_discovery':
        assert plan['startup_profile']==dict(path=str(OUT/'startup_profile.json'),pin=pin((OUT/'startup_profile.json').read_bytes()))
        assert plan['import_profile'] is None
    else:assert plan['startup_profile'] is plan['import_profile'] is None''')
    # A new child contract needs a fresh parent parser; legacy consumer receipts
    # must never be adopted by the new diagnostic merely because rc == 0.
    source=replace(source,"    return POST.compare(SimpleNamespace(**globals()),case,code,stdout,stderr,child_code,identity,argv,writer_errors)",
        "    raise ValueError('construction parent terminal oracle and workflow admission remain open')")
    paths=PATHS_FUNCTION.split('\n\ndef check_producer_helpers(',1)[0]
    return (source+paths+'''

def producer_references():
    return {key:dict(path=path,pin=pin(Path(path).read_bytes())) for key,path in producer_helper_paths().items()}
''').encode('utf8')


def current():
    pins={};methods={}
    for name,before,after in PAIRS:
        raw=globals()[name]((ROOT/before).read_text(encoding='utf8'))
        assert (ROOT/after).read_bytes()==raw,'successor differs from exact transform'
        compile(raw,str(ROOT/after),'exec',dont_inherit=True,optimize=0)
        pins[after]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    raw=loader_source();assert (ROOT/LOADER_PATH).read_bytes()==raw
    compile(raw,str(ROOT/LOADER_PATH),'exec',dont_inherit=True,optimize=0)
    pins[LOADER_PATH]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    return None,dict(schema='staged_saved_F_project_bootstrap_wiring_v1',authority='DRAFT_NONAUTHORITATIVE',
        successor_pins=pins,actual_source49_execs=0,P1_reads=0,issuer_implemented=False,
        parent_terminal_oracle_implemented=False,whole_workflow_admitted=False,formal_result=False,actual_F=False)


def create():
    for name,before,after in PAIRS:
        raw=globals()[name]((ROOT/before).read_text(encoding='utf8'))
        compile(raw,str(ROOT/after),'exec',dont_inherit=True,optimize=0)
        path=ROOT/after
        if path.exists():assert path.read_bytes()==raw
        else:
            with path.open('xb') as stream:stream.write(raw)
    path=ROOT/LOADER_PATH;raw=loader_source()
    if path.exists():assert path.read_bytes()==raw
    else:
        with path.open('xb') as stream:stream.write(raw)


if __name__=='__main__':create()
