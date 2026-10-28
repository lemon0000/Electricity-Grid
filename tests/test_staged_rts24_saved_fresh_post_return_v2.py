"""Frozen finite regressions and post-return fault tests; no scientific import."""
import ast
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
from types import FunctionType,MethodType,ModuleType,SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[1]


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


legacy=load('tests/test_staged_rts24_saved_fresh_none_census2048_v1.py','_frozen_finite_tests')
constructor=load('experiments/staged_rts24_saved_fresh_post_return_transform_v2.py','_post_constructor')
validation=load('experiments/staged_rts24_saved_fresh_post_return_validation_v1.py','_post_validation')
core=load('experiments/staged_rts24_saved_fresh_pre_entry_lease_v36.py','_post_core')
parent=load('experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v33.py','_post_parent')
namespace=load('experiments/staged_rts24_saved_fresh_entry_namespace_post_return_v1.py','_post_namespace')
HELPER=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v2.py'
legacy.native.HELPER=HELPER
legacy.native.PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v34.py'
legacy.native.logical.PROBE=legacy.native.PROBE


def helper():
    return legacy.native.logical.helper(HELPER,'_post_logical_helper')


def authentication_guard(module):
    context={};exec('def finder(value=None):return value',context)
    fn=context['finder'];plan=(None,)*8+((('finder',fn.__code__,1),),)
    g=SimpleNamespace(_state=('ACTIVE',True,0,1,0,0,False,''),_busy=False,_observed_stage=2,_authenticated_stage=0,
        _finder_authenticated=(),_finder_bindings=((plan,object(),context,object(),object(),(),()),),_audit_entry=lambda:None,_image=lambda:())
    def fault(name,error=None):raise module.BootstrapImportRejected(name) from error
    g._fault=fault
    g._check_finder_authentication=MethodType(module.BootstrapImportBoundary._check_finder_authentication,g)
    return g,fn


def clone(method,updates):
    return FunctionType(method.__code__,{**method.__globals__,**updates},method.__name__,method.__defaults__,method.__closure__)


class PostReturnTests(legacy.None2048Tests):
    def test_15_constructor_and_exact_return_identity(self):
        for name,before,after in (
            ('core','experiments/staged_rts24_saved_fresh_pre_entry_lease_v34.py','experiments/staged_rts24_saved_fresh_pre_entry_lease_v36.py'),
            ('probe','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v32.py','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v34.py'),
            ('parent','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v31.py','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v33.py'),
            ('helper','experiments/staged_rts24_saved_fresh_bootstrap_import_census2048_v1.py','experiments/staged_rts24_saved_fresh_bootstrap_post_return_v2.py'),
            ('namespace','experiments/staged_rts24_saved_fresh_entry_namespace_timing_v1.py','experiments/staged_rts24_saved_fresh_entry_namespace_post_return_v1.py')):
            self.assertEqual(getattr(constructor,name)((ROOT/before).read_text(encoding='utf-8')),(ROOT/after).read_bytes())
        old=legacy.fixture.BS;old_probe=legacy.fixture.PROBE
        try:
            legacy.fixture.BS=HELPER
            legacy.fixture.PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v34.py'
            module,sink=legacy.fixture.helper();guard,runtime,*_=legacy.fixture.guard_for(module);result=object()
            self.assertIs(module.diagnostic_import_once(runtime,_importer=lambda name:result),result)
            self.assertTrue(module._POST_METRICS['returned'])
            rows=[json.loads(x) for x in sink.getvalue().splitlines()]
            self.assertEqual([r[1] for r in rows if r[0]=='stage'],['before_adapter_import','adapter_import_returned','after_adapter_import_attempt'])
            self.assertEqual([r[1]['reason'] for r in rows if r[0]=='census'],['begin','import_return_before2048'])
        finally:legacy.fixture.BS=old;legacy.fixture.PROBE=old_probe

    def test_16_authentication_stages_getters_and_metadata_mutations(self):
        module=helper();module._POST_METRICS['returned']=True;g,fn=authentication_guard(module)
        captured=[];active=[True]
        g._event_sets=((),(),());token=object()
        def hook(event,args):
            if active[0] and event=='object.__getattr__' and args[0] is fn:
                captured.append((args[1],g._busy));module.BootstrapImportBoundary._audit(g,event,args,token,())
        sys.addaudithook(hook)
        try:
            self.assertIs(module.BootstrapImportBoundary.authenticate_machinery(g),g)
            self.assertEqual(g._authenticated_stage,2);self.assertTrue(captured)
            self.assertTrue(all(not busy for _,busy in captured))
            for field,value in (('__defaults__',tuple([None])),('__kwdefaults__',{})):
                before=getattr(fn,field)
                setattr(fn,field,value)
                try:
                    if field=='__defaults__':self.assertIsNot(fn.__defaults__,g._finder_authenticated[0][2])
                    with self.assertRaises(module.BootstrapImportRejected):g._check_finder_authentication()
                finally:setattr(fn,field,before)
            with self.assertRaises(module.BootstrapImportRejected):module.BootstrapImportBoundary.authenticate_machinery(g)
            for busy,stage,terminal in ((True,2,False),(False,1,False),(False,2,True)):
                other,_=authentication_guard(module);other._busy=busy;other._observed_stage=stage
                other._state=(*other._state[:6],terminal,'')
                with self.assertRaises((ValueError,module.BootstrapImportRejected)):module.BootstrapImportBoundary.authenticate_machinery(other)
            other,_=authentication_guard(module);other._observed_stage=1
            clock_calls=[]
            def bad_clock():
                clock_calls.append(1)
                if len(clock_calls)==2:raise OSError('injected_post_observation')
                return 1.0
            with self.assertRaises(module.BootstrapImportRejected) as kept:module.BootstrapImportBoundary.authenticate_machinery(other,_post_clock=bad_clock)
            self.assertIsInstance(kept.exception.__cause__,BaseExceptionGroup)
            self.assertTrue(any(isinstance(e,OSError) for e in kept.exception.__cause__.exceptions))
        finally:active[0]=False

    def test_17_graph_freshness_gates_class_function_and_output_cap(self):
        module=helper();adapter=ModuleType('src.staged_rts24_saved_fresh_adoption_v1')
        exec('GATES={"formal_result":False}\nclass HeldInput: pass\ndef validate(value=None):return value',vars(adapter))
        reader=(FunctionType,namespace.freeze_namespace_graph.__code__,vars(namespace),namespace.freeze_namespace_graph.__defaults__)
        image,objects=namespace.freeze_namespace_graph(adapter);proof=(reader,image,objects)
        module.check_adapter_roots(adapter,proof)
        for change,undo in (
            (lambda:adapter.GATES.update(formal_result=True),lambda:adapter.GATES.update(formal_result=False)),
            (lambda:setattr(adapter.HeldInput,'extra',1),lambda:delattr(adapter.HeldInput,'extra')),
            (lambda:setattr(adapter.validate,'__defaults__',(1,)),lambda:setattr(adapter.validate,'__defaults__',(None,)))):
            change()
            try:
                with self.assertRaises(ValueError):module.check_adapter_roots(adapter,proof)
            finally:undo()
        sink=io.BytesIO();stats={'calls':0}
        kw=dict(_clock=time.perf_counter,_write=sink.write,_flush=sink.flush,_dumps=json.dumps,_stats=stats)
        namespace.timed_namespace_graph(adapter,**kw)
        parsed=validation.parse(parent,sink.getvalue());self.assertEqual(parsed['graph_counts'],dict(namespace=0,adapter=1))
        self.assertTrue(parsed['graph_complete']);self.assertEqual(parsed['graph_frames'][1][5:7],[len(image),len(objects)])
        stats['calls']=40
        with self.assertRaisesRegex(ValueError,'call cap'):namespace.timed_namespace_graph(adapter,**kw)
        raw=sink.getvalue()
        for bad in (raw.rsplit(b'\n',2)[0]+b'\n',raw.replace(b'"exit"',b'"enter"'),raw.replace(b'"adapter"',b'"foreign"'),raw+b'["graph",41,"adapter","enter",1.0]\n'):
            try:value=validation.parse(parent,bad)
            except (AssertionError,ValueError):continue
            self.assertFalse(value['graph_complete'])

    def test_18_source49_freshness_and_retention_missing(self):
        sources=tuple(('fixture/'+str(i),str(i).encode()) for i in range(49));held={name:raw for name,raw in sources}
        runtime=SimpleNamespace(_raw=b'fixture',_sources=sources,_source_bookends=0)
        function=clone(core.LocalRuntimeInputs.source_bookend,dict(check_plan=lambda raw:dict(source_pins={n:core.pin(v) for n,v in sources}),read_file=lambda path,pin:held[str(path.relative_to(core.ROOT)).replace('\\','/')]))
        function(runtime);self.assertEqual(runtime._source_bookends,1)
        held[sources[24][0]]=b'changed'
        with self.assertRaisesRegex(ValueError,'source changed'):function(runtime)
        self.assertEqual(runtime._source_bookends,1)
        tree=ast.parse(HELPER.read_bytes());loader=next(n for n in tree.body if type(n) is ast.FunctionDef and n.name=='load_bootstrap_adapter')
        checks=[n for n in loader.body if type(n) is ast.Expr and type(n.value) is ast.Call and type(n.value.func) is ast.Name and n.value.func.id=='require' and any(type(x) is ast.Constant and x.value=='initial B_S modules changed' for x in ast.walk(n))]
        self.assertEqual(len(checks),1)
        marker=object();context=dict(require=core.require,sys=SimpleNamespace(modules={'held':marker}),boundary=SimpleNamespace(_module_initial=(('held',marker),)))
        unit=compile(ast.Module(body=checks,type_ignores=[]),'<retention-held-check>','exec')
        exec(unit,context);context['sys'].modules.clear()
        with self.assertRaisesRegex(ValueError,'initial B_S modules changed'):exec(unit,context)

    def test_19_closed_boundary_finish_failure_preserves_runtime_failure(self):
        def spec(fn):return FunctionType,fn.__code__,fn.__globals__,fn.__defaults__
        boundary=SimpleNamespace(_adapter=object(),_runtime_bindings=(object(),),_retention=(('held',object()),))
        phase=lambda owner:'CLOSED'
        profile=lambda owner:b'{}'
        runtime=SimpleNamespace(_phase='IMPORTING',_audit_handed_off=True,_boundary=boundary,_boundary_phase=spec(phase),
            _boundary_profile=spec(profile),_raw=b'fixture',entry=lambda:None,source_bookend=lambda:None)
        function=clone(core.LocalRuntimeInputs.finish_import,dict(check_plan=lambda raw:dict(import_profile=None),control_image=lambda:(),runtime_seal=lambda owner:('seal',)))
        runtime.entry=lambda:runtime
        self.assertEqual(function(runtime,boundary._adapter,boundary._runtime_bindings,boundary._retention),b'{}')
        self.assertEqual(runtime._phase,'OBSERVED')
        runtime._phase='IMPORTING'
        def fail(owner):raise ValueError('injected_after_boundary_close')
        runtime._boundary_profile=spec(fail)
        with self.assertRaisesRegex(ValueError,'after_boundary_close') as caught:function(runtime,boundary._adapter,boundary._runtime_bindings,boundary._retention)
        self.assertEqual(runtime._phase,'IMPORTING');self.assertEqual(phase(boundary),'CLOSED')
        missing=tuple(boundary._retention)
        with self.assertRaises(ValueError):function(runtime,boundary._adapter,boundary._runtime_bindings,tuple([*missing]))
        def cleanup(resource,owner,primary=None):resource.pending=[False,False];resource.phase='CLOSED'
        resource=SimpleNamespace(creator=('fixture',1),pending=[True,True],phase='LIVE',guard={'active':True},_early=None)
        ownership=(None,None,cleanup.__code__,object(),BaseException)
        runtime._cleanup_started=False;runtime._failure=None;runtime._resource=resource;runtime._ownership=ownership
        runtime._cleanup_seal=(id(resource),id(ownership),id(ownership[2]),id(ownership[3]),id(ownership[4]),resource.creator)
        runtime._boundary_finish=spec(lambda owner,primary=None:None)
        runtime._namespace_specs=(None,None,spec(lambda namespace,owner:None));runtime._namespace=SimpleNamespace()
        with self.assertRaises(core.LocalRuntimeUnresolved) as terminal:core.LocalRuntimeInputs.close(runtime,caught.exception)
        self.assertIs(terminal.exception.primary,caught.exception);self.assertEqual(runtime._phase,'UNRESOLVED')
        self.assertEqual(resource.phase,'CLOSED');self.assertEqual(resource.pending,[False,False]);self.assertFalse(resource.guard['active'])
        with self.assertRaises(core.LocalRuntimeUnresolved) as repeated:core.LocalRuntimeInputs.close(runtime)
        self.assertIs(repeated.exception,terminal.exception)
        module=helper();policy=(ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v7_non_authoritative/import_policy.json').read_bytes()
        for target in range(1,6):
            calls=[]
            def read_failure(path,pin,links=False):
                calls.append(path)
                if len(calls)==target:raise OSError('injected_external_read_'+str(target))
                return b'preceding_mock_read'
            inputs=clone(module._saved_import_inputs,dict(_READ_FILE=read_failure))
            close=clone(module.BootstrapImportBoundary.close,dict(_saved_import_inputs=inputs))
            b=SimpleNamespace(_state=('ACTIVE',True,1,1,0,0,False,''),_failure=None,_expected_bindings=(),_entry=lambda:None,
                _ownership=lambda:((0,core.get_ident()),None,None),_image=lambda:(),_profile_raw=policy,_numpy_state=(object(),False),
                _observed_stage=2,_authenticated_stage=2,_handoff_seen=1,_first_error=None)
            with self.assertRaises(module.BootstrapImportUnresolved) as external:close(b)
            self.assertEqual(len(calls),target);self.assertEqual(b._state[0],'FAULTED');self.assertFalse(b._state[1])
            self.assertEqual(external.exception.cleanup[0][0],'external_bookend')
            self.assertIn('injected_external_read_',str(external.exception.cleanup[0][1]))
            before=len(calls)
            with self.assertRaises(module.BootstrapImportUnresolved) as repeated:close(b)
            self.assertIs(repeated.exception,external.exception);self.assertEqual(len(calls),before)
        self.assertFalse(validation.terminal_complete(dict(post_return_terminal_complete=False),None))

    def test_20_parent_rejects_partial_completion_and_layers(self):
        value=legacy.record('import_return_before2048',2)
        value.update(schema='staged_saved_F_runtime_handoff_probe_v2',runtime_phase_before_close=None,post_metrics=None,graph_calls=0)
        for phase in ('CLOSED','UNRESOLVED'):
            changed=copy.deepcopy(value);changed['boundary_phase']='CLOSED';changed['runtime_phase']=phase
            with self.assertRaises(AssertionError):validation.validate_success(changed,dict(),parent)
        self.assertFalse(validation.terminal_complete(None,None))
        self.assertFalse(validation.terminal_complete(dict(post_return_terminal_complete=True),'timeout'))
        self.assertTrue(validation.terminal_complete(dict(post_return_terminal_complete=True),None))
        _,raw,_,_=legacy.run_window(8,2)
        argv=['layered-post-return'];value['kernel_identity']['command_line_sha']=parent.pin(parent.subprocess.list2cmdline(argv).encode())
        result=validation.compare(parent,'import_discovery',b'',parent.canonical(value)+b'\n',raw,1,dict(pid=value['kernel_identity']['pid'],creation=value['kernel_identity']['process_creation_filetime']),argv,[])
        self.assertEqual(result['child_record']['primary'],value['primary'])
        self.assertEqual(result['child_record']['secondary'],value['secondary'])
        self.assertFalse(result['post_return_terminal_complete'])
        parsed=validation.parse(parent,raw);first,last=parsed['census_frames'][0],parsed['census_frames'][-1]
        start=first['start_clock'];end=last['snapshot_clock']
        clocks=[start-2.0,start-1.0,end+0.1,end+0.2,*[end+0.3+i*0.01 for i in range(18)]]
        parsed.update(stages=[['stage',name,clock] for name,clock in zip(validation.STAGES,clocks)],
            graph_complete=True,stage_parse_complete=True,graph_counts=dict(namespace=21,adapter=9))
        n,a='namespace','adapter'
        parsed['graph_intervals']={'<before_loader_ready>':[n]*15,'before_source_bytes':[n],'before_adapter_roots':[a],
            'before_boundary_close':[a,a],'before_profile':[a],'before_finish_import':[n,a,a,n,a,n,a],
            'before_final_runtime_close':[n,a,n]}
        parsed['census_stage_intervals']=['before_adapter_import','adapter_import_returned']
        parsed['graph_frames']=[]
        for seq in range(1,31):
            kind='namespace' if seq<=21 else 'adapter'
            parsed['graph_frames'].extend([['graph',seq,kind,'enter',1.0+seq],['graph',seq,kind,'exit',1.1+seq,1,1,4]])
        profile=dict(schema='staged_saved_F_B_S_import_observation_v1',authority='DRAFT_NONAUTHORITATIVE',modules=[['held','module',None,None,'held.Loader']],
            cache=[['held','None']],paths=['held']*6,finder_types=['held.Finder'],machinery_observed=2,machinery_authenticated=2,optional_attempts=1,
            loaded_python_graph_attested=False,registry_contents_verified=False,native_behavior_verified=False)
        good=copy.deepcopy(value)
        good.update(status='completed',primary=None,secondary=[],failure_phase=None,runtime_phase_before_close='OBSERVED',runtime_phase='CLOSED',resource_phase='CLOSED',
            boundary_phase='CLOSED',source_bookends=5,retained_modules=1,import_profile=profile,graph_calls=30,
            post_metrics=dict(returned=True,idle_getter_events=100,busy_getter_events=0,**{name:[count,0.1,0.1] for name,count in (('authenticate',1),('finder_check',10),('adapter_check',8),('profile',2))}))
        good['boundary_report'].update(machinery_observed_stage=2,machinery_authenticated_stage=2,machinery_authentication_pending=False,
            source49_bookend_equal=True,import_boundary_completed=True,violations=0,phase='CLOSED',finder_function_metadata_bookend_verified=True,forced_numpy_SVE_false=True,
            optional_Popen_attempts=1,blocked_optional_attempts=1,installation_sentinel_observed=1,audit_handoff_observed=1)
        self.assertTrue(validation.validate_success(good,parsed,parent)['accepted'])
        # Build a complete raw chronology independently of the parser's interval projection.
        whole=[];seq=0
        def graph(kind,clock):
            nonlocal seq
            seq+=1;whole.extend([['graph',seq,kind,'enter',clock],['graph',seq,kind,'exit',clock+0.0001,1,1,4]])
        for i in range(15):graph(n,start-4.0+i*0.001)
        before_return=parsed['census_frames'][-2]['snapshot_clock'];returned=(before_return+end)/2
        stage_clocks=[start-2.0,start-1.0,returned,end+0.01,*[end+0.1+i*0.1 for i in range(18)]]
        for name,clock in zip(validation.STAGES,stage_clocks):
            whole.append(['stage',name,clock])
            if name=='before_adapter_import':whole.extend(['census',frame] for frame in parsed['census_frames'][:-1])
            if name=='adapter_import_returned':whole.append(['census',last])
            for i,kind in enumerate(parsed['graph_intervals'].get(name,())):graph(kind,clock+0.001+i*0.001)
        whole_raw=b''.join(parent.canonical(row)+b'\n' for row in whole)
        reopened=validation.parse(parent,whole_raw)
        self.assertEqual(seq,30);self.assertTrue(validation.validate_success(good,reopened,parent)['accepted'])
        reordered=whole[2:4]+whole[:2]+whole[4:]
        with self.assertRaises(AssertionError):validation.parse(parent,b''.join(parent.canonical(row)+b'\n' for row in reordered))
        for name,replacement in (('runtime_phase_before_close','IMPORTING'),('resource_phase','LIVE'),('source_bookends',4),('graph_calls',31),('runtime_was_live',True)):
            bad=copy.deepcopy(good);bad[name]=replacement
            with self.assertRaises(AssertionError):validation.validate_success(bad,parsed,parent)
        bad=copy.deepcopy(good);bad['post_metrics']['finder_check'][0]=9
        with self.assertRaises(AssertionError):validation.validate_success(bad,parsed,parent)
        for mode in ('record_extra','guard_extra','boundary_extra','boundary_authority','interval'):
            bad=copy.deepcopy(good);d=copy.deepcopy(parsed)
            if mode=='record_extra':bad['extra']=False
            elif mode=='guard_extra':bad['guard']['extra']=0
            elif mode=='boundary_extra':bad['boundary_report']['extra']=False
            elif mode=='boundary_authority':bad['boundary_report']['run_authority']=True
            else:d['graph_intervals']['before_source_bytes']=[a]
            with self.assertRaises(AssertionError):validation.validate_success(bad,d,parent)
        validation.profile_shape(profile)
        import zlib,base64
        raw_profile=parent.canonical(profile);encoded=dict(encoding='zlib_base64',raw_pin=parent.pin(raw_profile),data=base64.b64encode(zlib.compress(raw_profile)).decode())
        good['import_profile']=encoded;raw_good=parent.canonical(good)+b'\n'
        self.assertEqual(validation.decode(parent,raw_good)['import_profile'],profile)
        for key,value in (('schema','wrong'),('native_behavior_verified',True),('modules',[]),('paths',['short'])):
            bad=copy.deepcopy(profile);bad[key]=value
            with self.assertRaises(AssertionError):validation.profile_shape(bad)

    def test_21_complete_fourteen_loader_bindings_and_rejection(self):
        raw=(ROOT/'src/staged_rts24_saved_fresh_adoption_v1.py').read_bytes();tree=ast.parse(raw)
        names=tuple(n.name for n in tree.body if type(n) is ast.FunctionDef)
        expected=('digest','sources','stamp','caller_image','capture','hold','bookend','project_metrics','validate_metrics','replay','_replay','validate_payload','bind_payload','compare_payloads')
        self.assertEqual(names,expected);self.assertEqual(len(set(names)),14)
        unit=compile(raw,str(ROOT/'src/staged_rts24_saved_fresh_adoption_v1.py'),'exec',dont_inherit=True,optimize=0)
        codes={c.co_name:c for c in unit.co_consts if type(c) is type(unit) and c.co_name in names}
        self.assertEqual(len(codes),14)
        def make():
            module=helper();adapter=ModuleType('src.staged_rts24_saved_fresh_adoption_v1');adapter.__file__=str(ROOT/'src/staged_rts24_saved_fresh_adoption_v1.py')
            for node in (n for n in tree.body if type(n) is ast.FunctionDef):
                defaults=tuple(ast.literal_eval(v) for v in node.args.defaults) or None
                fn=FunctionType(codes[node.name],vars(adapter),node.name,defaults)
                fn.__kwdefaults__={arg.arg:ast.literal_eval(value) for arg,value in zip(node.args.kwonlyargs,node.args.kw_defaults) if value is not None} or None
                vars(adapter)[node.name]=fn
            numpy=ModuleType('numpy.testing._private.utils');numpy.__file__=str(ROOT/'tests/_synthetic_numpy.py');numpy._SUPPORTS_SVE=False
            modules={'numpy.testing._private.utils':numpy,'src.staged_rts24_saved_fresh_adoption_v1':adapter};events=[]
            fake_sys=SimpleNamespace(modules=modules,audit=lambda *args:events.append(args[0]))
            boundary=SimpleNamespace(_numpy_path=numpy.__file__,_image=lambda:(),_module_initial=tuple(modules.items()),_phase='PATH6')
            boundary.phase=lambda:boundary._phase
            boundary.begin_import=lambda:setattr(boundary,'_phase','ACTIVE')
            boundary.authenticate_machinery=lambda:None
            boundary.close=lambda:setattr(boundary,'_phase','CLOSED')
            runtime=SimpleNamespace(_boundary=boundary,_boundary_bindings=(None,)*4+((),),entry=lambda:None,
                source_bookend=lambda:{'src/staged_rts24_saved_fresh_adoption_v1.py':core.pin(raw)},source_bytes=lambda name:raw,
                _namespace=SimpleNamespace(_graph_plan=(None,None,None,(None,None,None,None,*module._CENSUS_IO))))
            frozen=[]
            def freeze(adapter_seen,raw_seen,runtime_seen):
                self.assertIs(adapter_seen,adapter);self.assertEqual(raw_seen,raw);self.assertIs(runtime_seen,runtime)
                self.assertEqual(tuple(n for n,*_ in boundary._runtime_bindings),expected);frozen.append(True);return ('synthetic_graph_proof',)
            function=clone(module.load_bootstrap_adapter,dict(sys=fake_sys,diagnostic_import_once=lambda owner:adapter,freeze_adapter_roots=freeze))
            return function,runtime,boundary,adapter,frozen,events
        function,runtime,boundary,adapter,frozen,events=make()
        result,bindings,retention=function(runtime,boundary)
        self.assertIs(result,adapter);self.assertIs(bindings,boundary._runtime_bindings);self.assertEqual(len(bindings),14)
        self.assertIs(retention,boundary._retention);self.assertEqual(len(retention),2);self.assertEqual(boundary._phase,'CLOSED')
        self.assertEqual(frozen,[True]);self.assertEqual(events,['electricity_grid.B_S.adapter_authenticated'])
        for mode in ('missing','same_name_wrong_code','default','kwdefault','source_order'):
            function,runtime,boundary,adapter,frozen,_=make()
            fn=adapter.compare_payloads
            if mode=='missing':del vars(adapter)['compare_payloads']
            elif mode=='same_name_wrong_code':
                replacement=FunctionType(adapter.digest.__code__,vars(adapter),'compare_payloads',fn.__defaults__);replacement.__kwdefaults__=fn.__kwdefaults__;vars(adapter)['compare_payloads']=replacement
            elif mode=='default':fn.__defaults__=(object(),)
            elif mode=='kwdefault':fn.__kwdefaults__={'unbound':None}
            else:
                changed=copy.deepcopy(tree);indices=[i for i,n in enumerate(changed.body) if type(n) is ast.FunctionDef]
                changed.body[indices[-1]],changed.body[indices[-2]]=changed.body[indices[-2]],changed.body[indices[-1]]
                runtime.source_bytes=lambda name:ast.unparse(changed).encode()
            with self.assertRaisesRegex(ValueError,'adapter (source|function|compiled)'):function(runtime,boundary)
            self.assertEqual(frozen,[])
