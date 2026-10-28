"""Create-only post-return diagnostic successors; original captures stay frozen."""
import ast
from pathlib import Path

ROOT=Path(__file__).absolute().parents[1]
OUT='staged_rts24_saved_fresh_nfc_v8_non_authoritative'
NAMESPACE='staged_rts24_saved_fresh_entry_namespace_post_return_v1.py'
HELPER='staged_rts24_saved_fresh_bootstrap_post_return_v1.py'
VALIDATOR='staged_rts24_saved_fresh_post_return_validation_v1.py'


def replace(source,pairs):
    for old,new,count in pairs:
        assert source.count(old)==count,(old,source.count(old),count)
        source=source.replace(old,new)
    return source


def edit_functions(source,updates):
    tree=ast.parse(source);lines=source.splitlines(keepends=True);changes=[]
    for node in ast.walk(tree):
        if type(node) is ast.FunctionDef and node.name in updates:
            update=updates[node.name];changed=update(node)
            indent=' '*(node.col_offset)
            raw='\n'.join(indent+line if line else '' for line in ast.unparse(changed).splitlines())+'\n'
            changes.append((node.lineno-1,node.end_lineno,raw))
    assert len(changes)==len(updates)
    for start,end,raw in sorted(changes,reverse=True):lines[start:end]=[raw]
    return ''.join(lines)


def core(source):
    source=replace(source,[('nfc_v7_non_authoritative','nfc_v8_non_authoritative',2),
        ('staged_rts24_saved_fresh_entry_namespace_timing_v1.py',NAMESPACE,1)])
    start=source.index('    def finish_import(');end=source.index('\n    def close(',start)
    body=replace(source[start:end],[('        return self.entry()','        self.entry();return observed',1)])
    return (source[:start]+body+source[end:]).encode()


def namespace(source):
    raw='''def timed_namespace_graph(module,_reader_code=freeze_namespace_graph.__code__,_fn=FunctionType,_ctx=globals(),_reader_defs=freeze_namespace_graph.__defaults__,
        _clock=_TRACE_CLOCK,_write=_TRACE_WRITE,_flush=_TRACE_FLUSH,_dumps=_TRACE_DUMPS,_base=BaseException,_stats=_GRAPH_STATS):
    typ,length,reject=_reader_defs[0][0],_reader_defs[0][2],_reader_defs[0][20]
    count=_stats['calls']
    if typ(count) is not _reader_defs[0][9] or not 0<=count<40:raise reject('diagnostic graph call cap')
    seq=count+1;_stats['calls']=seq
    kind='adapter' if module.__name__=='src.staged_rts24_saved_fresh_adoption_v1' else 'namespace'
    _write((_dumps(('graph',seq,kind,'enter',_clock()),separators=(',',':'))+'\\n').encode('ascii'));_flush()
    primary=None;sizes=(None,None,None)
    try:
        image,objects=_fn(_reader_code,_ctx,'held_original_graph',_reader_defs)(module)
        raw=_dumps(image,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
        if length(raw)>4194304:raise reject('diagnostic graph image cap')
        sizes=(length(image),length(objects),length(raw))
        return image,objects
    except _base as error:primary=error;raise
    finally:
        try:_write((_dumps(('graph',seq,kind,'exit',_clock(),*sizes),separators=(',',':'))+'\\n').encode('ascii'));_flush()
        except _base as output_error:
            if primary is None:raise
            raise primary from output_error
'''
    source=source.replace('def timed_namespace_graph(',"_GRAPH_STATS={'calls':0}\n\ndef timed_namespace_graph(",1)
    return edit_functions(source,{'timed_namespace_graph':lambda n:ast.parse(raw).body[0]}).encode()


def helper(source):
    source=replace(source,[("raise _stop('diagnostic_import_return_before2048')","_post_stats['returned']=True\n        return result",1),
        ('_trace=trace_import_stage):','_trace=trace_import_stage, _post_stats=_POST_METRICS):',1)])
    first=source.index('\nclass AuditCensusStop')
    source=source[:first]+"\n_POST_METRICS=dict(returned=False,idle_getter_events=0,busy_getter_events=0,authenticate=[0,0.0,0.0],finder_check=[0,0.0,0.0],adapter_check=[0,0.0,0.0],profile=[0,0.0,0.0])\n"+source[first:]
    def timed(name):
        def update(node):
            doc=node.body[:1] if type(node.body[0]) is ast.Expr and type(node.body[0].value) is ast.Constant and type(node.body[0].value.value) is str else []
            body=node.body[len(doc):]
            extra=ast.parse('def f(_post_metrics=_POST_METRICS,_post_clock=_CENSUS_IO[0],_post_max=max,_post_base=BaseException,_post_group=BaseExceptionGroup):pass').body[0]
            node.args.args.extend(extra.args.args);node.args.defaults.extend(extra.args.defaults)
            setup=ast.parse('_post_primary=None;_post_running=False').body
            start=ast.parse("if _post_metrics['returned']:\n _post_started=_post_clock();_post_row=_post_metrics[%r];_post_row[0]+=1;_post_running=True"%name).body
            finish=ast.parse('''if _post_running:
 try:
  _post_elapsed=_post_clock()-_post_started;_post_row[1]+=_post_elapsed;_post_row[2]=_post_max(_post_row[2],_post_elapsed)
 except _post_base as _post_error:
  if _post_primary is not None and _post_error is not _post_primary:
   _post_errors=[_post_error]
   if _post_primary.__cause__ is not None and _post_primary.__cause__ is not _post_primary:_post_errors.insert(0,_post_primary.__cause__)
   raise _post_primary from _post_group('post-return observation failed',_post_errors)
  raise
''').body
            handler=ast.ExceptHandler(type=ast.Name(id='_post_base',ctx=ast.Load()),name='_post_error',body=ast.parse('_post_primary=_post_error\nraise').body)
            node.body=doc+setup+[ast.Try(body=start+body,handlers=[handler],orelse=[],finalbody=finish)]
            return ast.fix_missing_locations(node)
        return update
    source=edit_functions(source,{'authenticate_machinery':timed('authenticate'),'_check_finder_authentication':timed('finder_check'),
        'check_adapter_roots':timed('adapter_check'),'profile_raw':timed('profile')})
    source=replace(source,[('_entry_fn=_audit_entry):','_entry_fn=_audit_entry, _post_stats=_POST_METRICS, _post_native=(dict, int, bool), _post_reject=ValueError):',1),
        ('        census_ticket = _begin(self, event)',
        "        if _type(_post_stats) is not _post_native[0] or _len(_post_stats) != 7 or _any(key not in _post_stats for key in ('returned','idle_getter_events','busy_getter_events','authenticate','finder_check','adapter_check','profile')):\n            raise _post_reject('post-return counter schema changed')\n        if _type(_post_stats['returned']) is not _post_native[2] or _any(_type(_post_stats[key]) is not _post_native[1] or not 0 <= _post_stats[key] <= 1000000 for key in ('idle_getter_events','busy_getter_events')):\n            raise _post_reject('post-return counter type changed')\n        if _post_stats['returned'] and self._state[1] and event == 'object.__getattr__':\n            _post_key = 'busy_getter_events' if self._busy else 'idle_getter_events'\n            if _post_stats[_post_key] == 1000000:raise _post_reject('post-return getter cap')\n            _post_stats[_post_key] += 1\n        census_ticket = _begin(self, event)",1),
        ('    boundary.authenticate_machinery()',"    trace_import_stage(runtime, 'before_machinery_authentication')\n    boundary.authenticate_machinery()",1),
        ("    raw = runtime.source_bytes('src/staged_rts24_saved_fresh_adoption_v1.py')","    trace_import_stage(runtime, 'before_source_bytes')\n    raw = runtime.source_bytes('src/staged_rts24_saved_fresh_adoption_v1.py')\n    trace_import_stage(runtime, 'after_source_bytes')",1),
        ("    trace_import_stage(runtime, 'after_adapter_roots')\n    runtime.source_bookend()","    trace_import_stage(runtime, 'after_adapter_roots')\n    trace_import_stage(runtime, 'before_final_source_bookend')\n    runtime.source_bookend()\n    trace_import_stage(runtime, 'after_final_source_bookend')",1),
        ("    require(all((name in sys.modules and sys.modules[name] is module for name, module in boundary._module_initial))", "    trace_import_stage(runtime, 'before_retention')\n    require(all((name in sys.modules and sys.modules[name] is module for name, module in boundary._module_initial))",1),
        ("    sys.audit('electricity_grid.B_S.adapter_authenticated', adapter)","    trace_import_stage(runtime, 'after_retention')\n    sys.audit('electricity_grid.B_S.adapter_authenticated', adapter)",1)])
    return source.encode()


def probe(source):
    source=replace(source,[('nfc_v7_non_authoritative','nfc_v8_non_authoritative',1),
        ("was_live=False","was_live=False;before_close=None",1),
        ("observed_profile=boundary.profile_raw();runtime.finish_import(adapter,adapter_bindings,retention)\n            runtime.entry();was_live=runtime._phase=='LIVE'",
         "bs_helper.trace_import_stage(runtime,'before_profile');observed_profile=boundary.profile_raw();bs_helper.trace_import_stage(runtime,'after_profile')\n            bs_helper.trace_import_stage(runtime,'before_finish_import');require(runtime.finish_import(adapter,adapter_bindings,retention)==observed_profile,'runtime profile/phase differs')\n            runtime.entry();before_close=runtime._phase;was_live=before_close=='LIVE';bs_helper.trace_import_stage(runtime,'after_finish_import')",1),
        ("            try:runtime_close[0]", "            try:bs_helper.trace_import_stage(runtime,'before_final_runtime_close')\n            except BaseException as error:secondary.append(error)\n            try:runtime_close[0]",1),
        ("                if error is not primary:secondary.append(error)\n        if namespace is not None:","                if error is not primary:secondary.append(error)\n            try:bs_helper.trace_import_stage(runtime,'after_final_runtime_close')\n            except BaseException as error:secondary.append(error)\n        if namespace is not None:",1),
        ("schema='staged_saved_F_runtime_handoff_probe_v1'","schema='staged_saved_F_runtime_handoff_probe_v2'",1),
        ('        runtime_was_live=was_live,',"        runtime_phase_before_close=before_close,post_metrics=None if bs_helper is None else bs_helper._POST_METRICS,\n        graph_calls=None if ns_helper is None else ns_helper._GRAPH_STATS['calls'],runtime_was_live=was_live,",1),
        ('_clock=helper._TRACE_CLOCK,','_stats=helper._GRAPH_STATS,_clock=helper._TRACE_CLOCK,',1),
        ('native[\'id\'],cls._audit_entry)',"native['id'],cls._audit_entry,namespace['_POST_METRICS'],(dict,native['int'],native['bool']),ValueError)",1),
        ("namespace['trace_import_stage'])", "namespace['trace_import_stage'],namespace['_POST_METRICS'])",1),
        ("        elif code.co_name=='_fault':", "        elif code.co_name in ('authenticate_machinery','_check_finder_authentication','check_adapter_roots','profile_raw'):expected=(namespace['_POST_METRICS'],census_io[0],native['max'],BaseException,native['BaseExceptionGroup'])\n        elif code.co_name=='_fault':",1)])
    source=replace(source,[(';before_close=None',';observed=None',1),(';before_close=runtime._phase',';observed=runtime._phase',1),
        ("was_live=before_close=='LIVE'","was_live=observed=='LIVE'",1),('runtime_phase_before_close=before_close,','runtime_phase_before_close=observed,',1)])
    return source.encode()


def parent(source):
    source=replace(source,[('nfc_v7_non_authoritative','nfc_v8_non_authoritative',1),('lease_v34.py','lease_v35.py',1),('probe_v32.py','probe_v33.py',1),
        ('staged_rts24_saved_fresh_bootstrap_import_census2048_v1.py',HELPER,2),('staged_rts24_saved_fresh_entry_namespace_timing_v1.py',NAMESPACE,2),
        ('staged_saved_F_runtime_handoff_probe_v1','staged_saved_F_runtime_handoff_probe_v2',3),
        ('if not prefix_terminal_complete(result,drain_reason):primary=\'finite_import_observation_incomplete\'',"if not POST.terminal_complete(result,drain_reason):primary='post_return_observation_incomplete'",1)])
    # The original census parser is retained; only the versioned stage vocabulary is extended.
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('_post_stage_contract',ROOT/'experiments'/VALIDATOR);v=module_from_spec(spec);spec.loader.exec_module(v)
    source=source.replace("    allowed = {'loader_ready',",'    allowed = set('+repr(v.STAGES)+') | {\'loader_ready\',',1)
    source+='''\n\nPOST=load(ROOT/'experiments/staged_rts24_saved_fresh_post_return_validation_v1.py','_post_return_validation')
def compare_child(case,code,stdout,stderr,child_code,identity,argv,writer_errors):
    from types import SimpleNamespace
    return POST.compare(SimpleNamespace(**globals()),case,code,stdout,stderr,child_code,identity,argv,writer_errors)
'''
    return source.encode()


def driver(source):
    source=replace(source,[('lease_v34.py','lease_v35.py',1),('probe_v32.py','probe_v33.py',1),('parent_v31.py','parent_v32.py',1),
        ('staged_rts24_saved_fresh_bootstrap_import_census2048_v1.py',HELPER,1),
        ('test_staged_rts24_saved_fresh_none_census2048_v1.py','test_staged_rts24_saved_fresh_post_return_v1.py',1),
        ('staged_rts24_saved_fresh_none_census2048_checkpoint_v1.py','staged_rts24_saved_fresh_post_return_checkpoint_v1.py',1),
        ('staged_deliverability_c_saved_fresh_census2048_admission_scope_v1.md','staged_deliverability_c_saved_fresh_post_return_admission_scope_v1.md',1),
        ('staged_rts24_saved_fresh_census2048_transform_v1.py','staged_rts24_saved_fresh_post_return_transform_v1.py',1),
        ("LEDGER=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v6_non_authoritative'", "NFC6=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v6_non_authoritative'\nLEDGER=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v7_non_authoritative'",1),
        ("LEDGER_SHA='5c5a2e47010031bb6b0da99fc9cd928917a590c91e04db2f9db88ea00d7daad3'","LEDGER_SHA='b56159068165115b54866169be5fb228cbaad6079081b79b85291443a8d58ce4'",1),
        ('CAPS=dict(unittest=14,pre_seal=4,discovery=5,profile_admission=4,audit_prefix=20,saved=4)','CAPS=dict(unittest=16,pre_seal=5,discovery=6,profile_admission=5,audit_prefix=30,saved=5)',1),
        ('STATIC_CAP=49;UNIT_CAP=14;TOTAL_CAP=63','STATIC_CAP=65;UNIT_CAP=16;TOTAL_CAP=81',1),
        ('SIZE_CAP=6;REGISTER_CAP=3;CHECKPOINT_CAP=3','SIZE_CAP=6;REGISTER_CAP=4;CHECKPOINT_CAP=4',1),
        ('MAX_FILES=16;','MAX_FILES=17;',1),
        ("'startup_profile.json':131072,","'unittest.exit.json':32768,'import_profile.json':1048576,'startup_profile.json':131072,",1),
        ("audit_prefix={'probe_import_discovery.plan.json','probe_import_discovery.receipt.json'}","audit_prefix={'probe_import_discovery.plan.json','probe_import_discovery.receipt.json','import_profile.json'}",1),
        ('CONSTRUCTOR,MEMORY,MEMORY_FIXTURE,Path(__file__).absolute()]',"CONSTRUCTOR,MEMORY,MEMORY_FIXTURE,ROOT/'experiments/"+NAMESPACE+"',ROOT/'experiments/"+VALIDATOR+"',Path(__file__).absolute()]",1),
        ("prior['all_cumulative_total_seconds']==830.1274519000538 and prior['package_charged_seconds']==33.30061389999173","prior['all_cumulative_total_seconds']==866.467895100049 and prior['package_charged_seconds']==36.34044319999521",1),
        ("prior['prefix_complete'] is True and prior['adapter_import_return_observed'] is False","prior['prefix_complete'] is False and prior['adapter_import_return_observed'] is True",1),
        ('==965896','==1138658',1),
        ('[trace_root,MEMO,UNIT_LEDGER,PREP_LEDGER,LEDGER]','[trace_root,MEMO,UNIT_LEDGER,PREP_LEDGER,NFC6,LEDGER]',1),
        ('len(archive)==57','len(archive)==73',1),('==4020082','==5158740',1),
        ("    for path,value in read(LEDGER/'registration.json')['input_pins'].items():\n        if path in result:assert result[path]==value,path\n        else:result[path]=value\n    assert len(result)==1072",
         "    for path,value in read(NFC6/'registration.json')['input_pins'].items():\n        if path in result:assert result[path]==value,path\n        else:result[path]=value\n    assert len(result)==1072\n    for path,value in read(LEDGER/'registration.json')['input_pins'].items():\n        if path in result:assert result[path]==value,path\n        else:result[path]=value\n    assert len(result)==1086",1),
        ('unit_tests_planned=14','unit_tests_planned=20',1),
        ('tests_run=14,failures=0','tests_run=20,failures=0',1),('assert len(rows)==30',"assert len(rows)==2*len(reg['unit_nodes'])+2",1),
        ("report['tests_run']==14","report['tests_run']==len(reg['unit_nodes'])",1),
        ("load(TEST,'none2048_tests')","load(TEST,'post_return_tests')",1),('result.testsRun==14','result.testsRun==20',1)])
    migration_raw='''def migration():
    constructor=load(CONSTRUCTOR,'_post_return_constructor')
    rows=(('core',ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v34.py',CORE),
        ('probe',ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v32.py',PROBE),
        ('parent',ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v31.py',PARENT),
        ('helper',ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_census2048_v1.py',HELPER),
        ('namespace',ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_timing_v1.py',ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_post_return_v1.py'))
    for name,before,after in rows:assert getattr(constructor,name)(before.read_text(encoding='utf-8'))==after.read_bytes(),name
    before=ast.parse(rows[-1][1].read_bytes());after=ast.parse(rows[-1][2].read_bytes())
    reader=lambda tree:next(n for n in tree.body if type(n) is ast.FunctionDef and n.name=='freeze_namespace_graph')
    assert ast.dump(reader(before))==ast.dump(reader(after))
    return dict(versioned_post_return=True,constructor_exact=True,original_graph_reader_unchanged=True,
        source49_unchanged=True,all_fresh_checks_retained=True,memory_stop_policy_unchanged=True,
        scientific_acceptance_threshold_change=False,diagnostic_only=True)
'''
    nodes_raw='''def nodes():
    paths=(ROOT/'tests/test_staged_rts24_saved_fresh_none_census2048_v1.py',NATIVE_TEST,TEST)
    classes=('None2048Tests','NativeImageTests','PostReturnTests');names=[]
    for path,name in zip(paths,classes):
        cls=next(n for n in ast.parse(path.read_bytes()).body if type(n) is ast.ClassDef and n.name==name)
        names.extend(n.name for n in cls.body if type(n) is ast.FunctionDef and n.name.startswith('test_'))
    assert len(names)==len(set(names))==20
    return sorted('post_return_tests.PostReturnTests.'+name for name in names)
'''
    bounds_raw='''def output_bounds():
    value=read(LEDGER/'checkpoint.json')['census_frames'][-1];high=float.fromhex('0x1.fffffffffffffp+1023')
    value.update(seq=20,reason='import_return_before2048',active=False,inflight=False,start_clock=-high,snapshot_clock=-high,
        entered=2048,passed=2048,rejected=2048,observed=2048,phase='globals_attrs',last_incomplete='globals_attrs',
        diagnostic_error_count=4,cache_items=4096,cache_new=4096,machinery_stage=2,installation_seen=1)
    value['buckets']={name:[2048,high,high] for name in value['buckets']}
    line=len(canonical(['census',value]))+1;census=20*line
    parent=load(PARENT,'_post_output_bounds');stages=parent.POST.STAGES
    graph=40*sum(max(len(canonical(row))+1 for row in candidates) for candidates in (
        [['graph',40,kind,'enter',-high] for kind in ('namespace','adapter')],
        [['graph',40,kind,'exit',-high,50000,50000,4194304] for kind in ('namespace','adapter')]))
    stage=sum(len(canonical(['stage',name,-high]))+1 for name in stages)
    assert line<=2048 and census<=24576 and census+graph+stage<=32768
    memory=load(MEMORY,'_post_memory_bound');guard=memory.initial_guard();metric=dict(working_set_bytes=268435456,peak_working_set_bytes=268435456,private_bytes=268435456)
    guard.update(attempts=4096,samples=4096,maxima={name:dict(metric) for name in ('parent','child')},last={name:dict(metric) for name in ('parent','child')},
        max_sum_peak_working_set_bytes=536870912,max_sum_private_bytes=536870912,native_sampler_bound=True,
        binding=dict(parent_pid=4294967294,child_pid=4294967295,child_handle=18446744073709551615,struct_bytes=80),drained_child_pid=4294967295)
    memory.validate_guard(guard)
    body=dict(accepted=True,authority=AUTHORITY,metadata_only=True,diagnostic_accepted=True,
        audit_validation=dict(accepted=True,terminal_mode='post_return_observed_closed',passed=2048,importer_return_observed=True,observed_before_close=True,boundary_completed=True,
            graph_counts=dict(namespace=40,adapter=40),source_bookends=5,selected_open_window_only=True,all_unselected_events_verified=False,candidate_adopted=False,resource_admission=False),
        stages=[],graph_frames=[],census_frames=[],memory_observation=dict(peak_working_set_bytes=None,error='x'*160),memory_guard=guard,
        memory_observation_source='last_live_memory_guard',drain_reason=None,runtime_phase_before_close='OBSERVED',
        import_profile_pin=dict(bytes=1048576,sha256='0'*64),post_metrics=dict(returned=True,idle_getter_events=999999999,busy_getter_events=999999999,
            **{name:[40,high,high] for name in parent.POST.METRICS}),all_unselected_events_verified=False,candidate_adopted=False,**flags())
    body_bytes=len(canonical(body));assert body_bytes<=4096
    return dict(census_frame_bytes=line,max_frames=20,normal_frames=18,census_upper_bytes=census,graph_call_cap=40,
        graph_upper_bytes=graph,stage_upper_bytes=stage,stderr_upper_bytes=census+graph+stage,saved_body_upper_bytes=body_bytes)
'''
    matrix_raw='''def audit_matrix(parent,row):
    result=parent.POST.audit(parent,row)
    assert (OUT/'import_profile.json').read_bytes()==canonical(row['result']['child_record']['import_profile'])
    return result
'''
    saved_raw='''def saved_report(parent,row):
    validation=audit_matrix(parent,row);child=row['result']['child_record']
    return dict(accepted=True,authority=AUTHORITY,metadata_only=True,diagnostic_accepted=True,audit_validation=validation,
        stages=row['result']['diagnostic']['stages'],graph_frames=row['result']['diagnostic']['graph_frames'],census_frames=row['result']['diagnostic']['census_frames'],
        memory_observation=row['memory_observation'],memory_guard=row['bounded_drain']['memory_guard'],memory_observation_source=row['memory_observation_source'],drain_reason=row['drain_reason'],
        runtime_phase_before_close=child['runtime_phase_before_close'],post_metrics=child['post_metrics'],import_profile_pin=pin((OUT/'import_profile.json').read_bytes()),
        all_unselected_events_verified=False,candidate_adopted=False,**flags())
'''
    updates={name:(lambda n,raw=raw:ast.parse(raw).body[0]) for name,raw in (
        ('migration',migration_raw),('nodes',nodes_raw),('output_bounds',bounds_raw),('audit_matrix',matrix_raw),('saved_report',saved_raw))}
    return edit_functions(source,updates).encode()


def checkpoint(source):
    source=replace(source,[('nfc_v7_non_authoritative','nfc_v8_non_authoritative',1),('unit_tests=14','unit_tests=20',1),
        ('parent.validate_prefix_stderr(stderr)','parent.POST.parse(parent,stderr)',1),
        ("finite_terminal_complete=receipt['result']['finite_terminal_complete']","post_return_terminal_complete=receipt['result']['post_return_terminal_complete']",1),
        ("adapter_import_attempts_upper_bound=1)","adapter_import_attempts_upper_bound=1,runtime_phase_before_close=receipt['result']['child_record']['runtime_phase_before_close'],post_metrics=receipt['result']['child_record']['post_metrics'],import_profile_pin=pin((OUT/'import_profile.json').read_bytes()))",1),
        ("packed_metadata_and_finite_import_diagnostic_only","packed_metadata_and_post_return_diagnostic_only",1),
        ('prior_archive_files=57,prior_archive_bytes=4020082','prior_archive_files=73,prior_archive_bytes=5158740',1)])
    return source.encode()


def write_successors():
    pairs=(('core','experiments/staged_rts24_saved_fresh_pre_entry_lease_v34.py','experiments/staged_rts24_saved_fresh_pre_entry_lease_v35.py'),
        ('probe','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v32.py','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v33.py'),
        ('namespace','experiments/staged_rts24_saved_fresh_entry_namespace_timing_v1.py','experiments/'+NAMESPACE),
        ('helper','experiments/staged_rts24_saved_fresh_bootstrap_import_census2048_v1.py','experiments/'+HELPER),
        ('parent','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v31.py','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v32.py'))
    for name,before,after in pairs:
        target=ROOT/after
        raw=globals()[name]((ROOT/before).read_text(encoding='utf-8'));compile(raw,str(target),'exec',dont_inherit=True,optimize=0)
        if target.exists():assert target.read_bytes()==raw
        else:target.write_bytes(raw)
    print('Created five versioned post-return diagnostic sources')


if __name__=='__main__':write_successors()
