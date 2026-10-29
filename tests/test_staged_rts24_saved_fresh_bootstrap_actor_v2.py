"""Bootstrap/quiet actors: private lifecycle and two fixed stdlib toy children."""
import ast
import builtins
import copy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from threading import Thread
from types import CodeType,FunctionType,SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[1]


def load(name,relative):
    path=ROOT/relative;spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


engine=load('_bootstrap_actor','experiments/staged_rts24_saved_fresh_bootstrap_actor_v1.py')
quiet=load('_parent_quiet_actor','experiments/staged_rts24_saved_fresh_parent_quiet_actor_v1.py')
wiring=load('_bootstrap_wiring','experiments/staged_rts24_saved_fresh_bootstrap_actor_transform_v1.py')
core=load('_bootstrap_core43','experiments/staged_rts24_saved_fresh_pre_entry_lease_v43.py')
parent=load('_construction_parent39','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v39.py')
drain=load('_complete_candidate_drain','experiments/staged_rts24_saved_fresh_memory_drain_v2.py')
old=load('_private_export_fixture','tests/test_staged_rts24_saved_fresh_producer_export_v2.py')
DRAIN_RAW=(ROOT/'experiments/staged_rts24_saved_fresh_memory_drain_v2.py').read_bytes()
COORDINATOR_RAW=(ROOT/'experiments/staged_rts24_saved_fresh_complete_producer_v2.py').read_bytes()

# Adapt only private text, preserving all frozen production and test files.
raw=old.legacy.CORE_RAW
assert raw.count(b"self._phase!='LIVE'")==1
raw=raw.replace(b"self._phase!='LIVE'",b"self._phase not in ('ADOPTED','IMPORTING','OBSERVED','LIVE')")
raw+=b'''
    def prepare_consumer(self):
        self.events.append(('prepare',self._phase,self._consume_state))
        if self.prepare_error is not None:
            if self.prepare_self_closes:self.close(self.prepare_error)
            raise self.prepare_error
        self._consumer_plan=self.prepared_plan;self._consume_state='PREPARED';self._seal=runtime_seal(self)
        return self
    def finish_import(self,adapter,bindings,retention):
        self.events.append(('finish',self._phase,self._consume_state))
        if self.finish_error is not None:raise self.finish_error
        self._adapter=adapter;self._adapter_bindings=bindings;self._retention=retention
        self._import_profile_matched=self.profile_matches
        self._phase='LIVE' if self.profile_matches else 'OBSERVED';self._seal=runtime_seal(self)
        if self.finish_callback is not None:self.finish_callback()
        return self.profile_raw
'''
old.legacy.CORE_RAW=raw


def source_guard():
    if BOX['error'] is not None:raise BOX['error']


def private_permission(held,operation,args):
    if operation=='install_guard':
        old.base.put(held[2],boundary=args[0],guard_phase='INSTALLED_DENY',sentinel=1);return
    return old.private_permission_dispatch(held,operation,args)


def private_bridge(state,stage,owner,args):
    if owner is not fixture.owner or args:raise ValueError('private same owner required')
    if stage=='report':
        return dict(schema='staged_saved_F_pre_admission_construction_v1',authority='DRAFT_NONAUTHORITATIVE',
            source_modules=37,loader_execs=36,entry_execs=2,bundle_phase='READY',P1_reads=0,admission_present=False)
    if stage=='bundle':
        if fixture.bundle_error is not None:raise fixture.bundle_error
        return state['bundle']
    if stage=='release':state['released']=True;return
    raise ValueError('private fixed bridge operation required')


def make_plan(case='producer'):
    # Closed metadata fixture, independent of unexecuted Native-root outputs.
    # Dummy policy/profile pins are never used for a real import or launch.
    folder=ROOT/wiring.NATIVE_ROOT
    def ref(path):return dict(path=str(path),pin=core.pin(path.read_bytes()))
    plan=dict(schema='staged_saved_F_complete_bootstrap_manifest_v1',authority='DRAFT_NONAUTHORITATIVE',
        nonce='1'*32,source_pins=parent.source(),source_epoch=core.SOURCE_SHA,
        bootstrap_pin=core.pin(b'# never executed synthetic transport\n'),executable_pin=core.pin(parent.EXE.read_bytes()),
        python=core._PYTHON,environment=parent.environment(),cwd=str(ROOT),initial_paths=list(core._PATHS),
        selected_runtime_file_observations={name:core.pin(Path(name).read_bytes()) for name in core.TCB_PATHS},
        startup_absent=list(core.STARTUP_ABSENT),startup_profile=None,
        namespace_helper=ref(ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v4.py'),
        import_helper=ref(ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v4.py'),
        import_policy=dict(path=str(folder/'import_policy.json'),pin=core.pin(b'{}')),import_profile=None,
        producer_helpers={name:ref(Path(path)) for name,path in core.producer_helper_paths().items()},
        graph_contract=core.construction_graph_contract(),case=case)
    plan['startup_profile']=None if case=='discovery' else dict(path=str(folder/'startup_profile.json'),pin=core.pin(b'{}'))
    plan['import_profile']=dict(path=str(folder/'import_profile.json'),pin=core.pin(b'{}')) if case=='producer' else None
    return plan


class BootstrapActorTests(unittest.TestCase):
    def fixture(self,mode='producer'):
        fixture=old.ExportLifecycleTests(methodName='test_55_coordinator_full_private_chain_and_quiet_data_replay')
        fixture.setUp();self.addCleanup(fixture.doCleanups);fixture.setup_coordinator()
        owner=fixture.owner;plan=owner._consumer_plan;adapter=fixture.adapter
        owner.prepared_plan=plan;owner.events=[];owner.prepare_error=None;owner.finish_error=None;owner.prepare_self_closes=False
        owner.profile_matches=mode=='producer';owner.profile_raw=b'ordinary-private-profile';owner.finish_callback=None
        owner._phase='ADOPTED';owner._consumer_plan=None;owner._consume_state=None;owner._adapter=None
        owner._seal=fixture.core.runtime_seal(owner)
        fixture.bindings=(('logical',),);fixture.retention=(('ordinary',object()),)
        owner._boundary._adapter=adapter;owner._boundary._runtime_bindings=fixture.bindings;owner._boundary._retention=fixture.retention
        old.base.put(fixture.permission,phase='DISABLED',guard_phase='NEW',admission=None)
        permission=(private_permission.__code__,dict(old=old),(None,None,fixture.permission))
        fixture.context['_P1_PERMISSION_PROGRAM']=permission
        # Original private bundle still executes real LC6 body/bookends/close.
        bridge=(private_bridge.__code__,dict(old=old,fixture=fixture),fixture.bridge[2])
        box=dict(error=None)
        context=fixture.context['_private_functions'](vars(engine))
        context.update(_RUNTIME_TYPE=type(owner),_GUARD=(source_guard.__code__,dict(BOX=box),( )),
            _COORDINATOR_RAW=COORDINATOR_RAW)
        context['_COORDINATOR_PROGRAM']=context['seal_program'](vars(old.coordinator))
        actor=context['new_actor'](owner,bridge,permission,old.base.RAW,mode)
        program=context['seal_program'](context)
        spec=(engine.actor_dispatch.__code__,dict(__builtins__=dict(vars(builtins)),FunctionType=FunctionType,CodeType=CodeType),
            (program,actor,engine.program_context.__code__,engine.dispatch.__code__))
        fixture.actor=actor;fixture.actor_spec=spec;fixture.actor_context=context;fixture.box=box;fixture.actor_permission=permission
        fixture.actor_call=lambda operation,args=():FunctionType(spec[0],spec[1])(spec[2],operation,args)
        return fixture

    def importing(self,fixture):
        fixture.owner._phase='IMPORTING';fixture.owner._seal=fixture.core.runtime_seal(fixture.owner)
        fixture.actor_call('install_guard',(fixture.owner._boundary,))

    def ready(self,fixture):
        self.importing(fixture)
        return fixture.actor_call('import_returned',(fixture.adapter,fixture.bindings,fixture.retention,fixture.owner.profile_raw))

    def private_issue_on_finish(self,fixture):
        def issue():
            old.base.put(fixture.permission,phase='ISSUED',guard_phase='READ_WINDOW',admission=fixture.token)
        fixture.owner.finish_callback=issue

    def test_01_full_private_order_and_terminal_release(self):
        fixture=self.fixture();self.private_issue_on_finish(fixture);self.ready(fixture)
        result=fixture.actor_call('run',(ROOT/'results/tables/synthetic_not_written',1.0))
        self.assertEqual(fixture.owner.events,[('prepare','IMPORTING',None),('finish','IMPORTING','PREPARED')])
        self.assertEqual(result['schema'],'staged_saved_F_complete_producer_data_v2')
        self.assertEqual(fixture.owner._resource.close_calls,[1,1]);self.assertEqual(fixture.actor._phase,'CLOSED')
        self.assertIsNone(fixture.actor._owner);self.assertIsNone(fixture.actor._cleanup)
        fixture.actor_call('close',(None,));self.assertEqual(fixture.owner.close_calls,1)
        self.assertIs(fixture.actor_call('observation')['actual_F'],False)

    def test_02_prepare_self_close_preserves_primary_without_second_close(self):
        fixture=self.fixture();primary=LookupError('consumer preparation');fixture.owner.prepare_error=primary
        fixture.owner.prepare_self_closes=True
        with self.assertRaises(fixture.core.LocalRuntimeUnresolved) as caught:self.ready(fixture)
        self.assertIs(caught.exception.primary,primary);self.assertIs(fixture.actor._failure,caught.exception)
        self.assertEqual(fixture.owner.close_calls,1);self.assertEqual(fixture.permission.guard_phase,'CLOSED')

    def test_03_prepare_failure_revoke_precedes_original_close(self):
        fixture=self.fixture();primary=ValueError('preparation before cleanup');fixture.owner.prepare_error=primary
        observed=[];fixture.owner.close_callback=lambda:observed.append(fixture.permission.guard_phase)
        with self.assertRaises(ValueError) as caught:self.ready(fixture)
        self.assertIs(caught.exception,primary);self.assertEqual(observed,['DENY']);self.assertEqual(fixture.owner.close_calls,1)

    def test_04_finish_failure_retains_original_and_prepared_slot(self):
        fixture=self.fixture();primary=ArithmeticError('profile return');fixture.owner.finish_error=primary
        with self.assertRaises(ArithmeticError) as caught:self.ready(fixture)
        self.assertIs(caught.exception,primary);self.assertEqual(fixture.owner._consume_state,'PREPARED')
        self.assertEqual(fixture.owner.close_calls,1);self.assertEqual(fixture.actor._phase,'FAILED')

    def test_05_unmatched_profile_is_not_live(self):
        fixture=self.fixture();fixture.owner.profile_matches=False
        with self.assertRaisesRegex(ValueError,'independent profile-matched LIVE'):self.ready(fixture)
        self.assertEqual(fixture.owner.close_calls,1);self.assertEqual(fixture.actor._phase,'FAILED')

    def test_06_incomplete_producer_close_none_is_failure(self):
        fixture=self.fixture();self.ready(fixture)
        with self.assertRaisesRegex(ValueError,'incomplete producer') as caught:fixture.actor_call('close',(None,))
        self.assertIs(fixture.actor._failure,caught.exception);self.assertEqual(fixture.actor._phase,'FAILED')
        self.assertEqual(fixture.owner.close_calls,1);self.assertIsNone(fixture.actor._result)

    def test_07_runtime_method_drift_uses_captured_original_close(self):
        fixture=self.fixture();function=type(fixture.owner).finish_import;original=function.__code__
        def replacement(*args):raise AssertionError('replacement must not execute')
        function.__code__=replacement.__code__
        try:
            with self.assertRaisesRegex(ValueError,'original bootstrap runtime method'):self.ready(fixture)
        finally:function.__code__=original
        self.assertEqual(fixture.owner.close_calls,1);self.assertEqual(fixture.permission.guard_phase,'CLOSED')

    def test_08_source_guard_fault_still_revokes_and_closes_once(self):
        fixture=self.fixture();primary=LookupError('source proof drift');fixture.box['error']=primary
        with self.assertRaises(LookupError) as caught:fixture.actor_call('import_bridge')
        self.assertIs(caught.exception,primary);self.assertEqual(fixture.owner.close_calls,1)
        self.assertEqual(fixture.permission.guard_phase,'CLOSED')

    def test_09_foreign_thread_cannot_close_actor_and_failure_is_sticky(self):
        fixture=self.fixture();errors=[]
        def foreign():
            try:fixture.actor_call('close',(None,))
            except BaseException as error:errors.append(error)
        thread=Thread(target=foreign);thread.start();thread.join(.5)
        self.assertFalse(thread.is_alive());self.assertEqual(len(errors),1);self.assertEqual(fixture.owner.close_calls,0)
        with self.assertRaises(ValueError) as first:fixture.actor_call('close',(None,))
        with self.assertRaises(ValueError) as second:fixture.actor_call('close',(None,))
        self.assertIs(first.exception,second.exception);self.assertEqual(fixture.owner.close_calls,1)

    def test_10_sealed_dispatch_and_coordinator_ignore_convenience_replacements(self):
        fixture=self.fixture();self.private_issue_on_finish(fixture);calls=[]
        def replacement(*args):calls.append(args);raise AssertionError('unapproved replacement')
        fixture.actor_context['dispatch']=replacement;fixture.actor_context['program_call']=replacement
        with patch.object(old.coordinator,'complete_producer',replacement),patch.object(old.coordinator,'coordinator_revoke',replacement):
            self.ready(fixture);fixture.actor_call('run',(ROOT/'results/tables/synthetic_not_written',1.0))
        self.assertEqual(calls,[]);self.assertEqual(fixture.owner.close_calls,1)

    def test_11_construction_observation_closes_without_consumer_or_issuer(self):
        fixture=self.fixture('import_discovery');result=self.ready(fixture)
        self.assertEqual(fixture.owner.events,[('finish','IMPORTING',None)])
        self.assertEqual(result['P1_reads'],0);fixture.actor_call('close',(None,))
        self.assertEqual(fixture.actor._phase,'CLOSED');self.assertIsNone(fixture.owner._consume_state)

    def test_12_actual_pinned_loader_returns_only_disabled_actor(self):
        fixture=self.fixture();plan=make_plan();fixture.owner._raw=core.canonical(plan)
        namespace={name:getattr(core,name) for name in ('builtins','check_plan','read_file','pin','decode','FunctionType','CodeType','producer_helper_paths','require')}
        namespace.update(LocalRuntimeInputs=type(fixture.owner),__file__=str(ROOT/'experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v4.py'))
        raw=(ROOT/'experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v4.py').read_bytes()
        exec(compile(raw,namespace['__file__'],'exec',dont_inherit=True,optimize=0),namespace,namespace)
        spec=namespace['prepare_project_bridge'](fixture.owner,plan,compile,exec)
        actor=spec[2][1];self.assertEqual(actor._phase,'ADOPTED');self.assertIs(actor._cleanup[1],fixture.owner)
        bridge=FunctionType(spec[0],spec[1])(spec[2],'import_bridge',())
        self.assertIs(bridge,actor._bridge)
        program=actor._permission
        self.assertEqual(program[2][2].phase,'DISABLED');self.assertIsNone(program[2][2].admission)
        with self.assertRaises(PermissionError):FunctionType(program[0],program[1])(program[2],'issue',())


class WiringTests(unittest.TestCase):
    def test_13_runtime_class_codetypes_are_unchanged(self):
        def runtime(path):
            unit=compile((ROOT/path).read_bytes(),'<same_core>','exec',dont_inherit=True,optimize=0)
            return next(code for code in unit.co_consts if type(code) is CodeType and code.co_name=='LocalRuntimeInputs')
        self.assertEqual(runtime('experiments/staged_rts24_saved_fresh_pre_entry_lease_v42.py'),runtime('experiments/staged_rts24_saved_fresh_pre_entry_lease_v43.py'))

    def test_14_manifest_closed_helpers_and_producer_profile(self):
        for case in ('discovery','import_discovery','producer'):core.check_plan(core.canonical(make_plan(case)))
        plan=make_plan()
        for mode in ('missing','old_profile','old_loader','extra_helper','graph'):
            bad=copy.deepcopy(plan)
            if mode=='missing':bad['import_profile']=None
            elif mode=='old_profile':bad['import_profile']['path']=str(ROOT/'paper/drafts/README.md')
            elif mode=='old_loader':bad['producer_helpers']['bootstrap_loader']['path']=str(ROOT/'experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v3.py')
            elif mode=='extra_helper':bad['producer_helpers']['invented']=bad['producer_helpers']['bootstrap_actor']
            else:bad['graph_contract']['whole_workflow_admitted']=True
            with self.subTest(mode=mode),self.assertRaises((TypeError,ValueError)):core.check_plan(core.canonical(bad))

    def test_15_source_derivation_and_separate_stop_caps(self):
        _,report=wiring.current();self.assertIs(report['resource_admission'],False)
        self.assertEqual(report['graph_stop_contract']['prior_construction_calls'],43)
        self.assertIsNone(report['graph_stop_contract']['observed_complete_calls'])
        self.assertEqual((drain.STDOUT_CAP,drain.STDERR_CAP),(327681,131072));drain.check_bindings()
        old_raw=(ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v3.py').read_bytes()
        new_raw=(ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v4.py').read_bytes()
        self.assertEqual(new_raw,old_raw.replace(b'not 0 <= count < 43:',b'not 0 <= count < 256:',1))

    def test_16_full_candidate_transport_stays_within_original_utf16_limit(self):
        code=parent.TRANSPORT.build(ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v43.py',
            ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v41.py',parent.minify_prefix)
        argv=[str(parent.EXE),'-P','-B','-s','-S','-c',code.decode('utf8'),'--pre-entry-lease',
            str(ROOT/wiring.NATIVE_ROOT/'probe_producer.plan.json'),'0'*64]
        self.assertLessEqual(len(subprocess.list2cmdline(argv).encode('utf-16-le'))//2,30000)


class ParentQuietTests(unittest.TestCase):
    def toy(self,exit_code,action,break_release=False):
        program='import sys,time,json,hashlib;raw=sys.stdin.buffer.read();time.sleep(.12);sys.stdout.buffer.write(json.dumps({"release_sha256":hashlib.sha256(raw).hexdigest()},sort_keys=True,separators=(",",":")).encode()+b"\\n");sys.stdout.buffer.flush();raise SystemExit('+str(exit_code)+')'
        argv=[sys.executable,'-B','-s','-S','-c',program]
        process=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        actor=None
        try:
            identity=quiet.kernel_identity(process)
            calls=[]
            def forged(*args):calls.append(args);raise AssertionError('forged closure must not run')
            def cell(value):return (lambda:value).__closure__[0]
            fake=FunctionType(drain.drain.__code__,vars(drain),'forged_same_code',drain.drain.__defaults__,
                tuple(cell(forged) for _ in drain.drain.__closure__))
            with self.assertRaisesRegex(ValueError,'fixed parent drain source'):
                quiet.capture(process,identity,argv,quiet.pin(b'plan'),quiet.pin(b'transport'),fake)
            self.assertEqual(calls,[])
            with patch.object(quiet,'kernel_identity',side_effect=AssertionError('public replacement must not run')):
                actor=quiet.capture(process,identity,argv,quiet.pin(b'plan'),quiet.pin(b'transport'),DRAIN_RAW)
            self.assertIsNone(actor._writer);self.assertEqual(actor._writer_errors,())
            if break_release:process.stdin.close()
            quiet.release(actor)
            return action(process,actor)
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=1.)
            if actor is not None and actor._writer is not None:actor._writer.join(.5)
            for stream in (process.stdin,process.stdout,process.stderr):
                if not stream.closed:stream.close()
            if not process._handle.closed:process._handle.Close()

    def test_17_real_toy_quiet_binds_original_drain_and_releases_live_refs(self):
        calls=[]
        def replacement():calls.append(True);raise AssertionError('global checker must not execute')
        def action(process,actor):
            with patch.object(drain,'check_bindings',replacement):
                rc,out,err,reason,returned=quiet.drain_child(actor,1.0)
                returned['killed']=True;returned['pipes_closed']=False
                quiet.close_handle(actor);result=quiet.finish(actor)
            self.assertEqual(rc,0);self.assertIsNone(reason);self.assertEqual(result['stdout_pin'],quiet.pin(out))
            self.assertEqual(json.loads(out)['release_sha256'],result['release_pin']['sha256'])
            self.assertEqual(result['kernel_identity']['pid'],process.pid);self.assertIs(result['quiet']['pipes_closed'],True)
            self.assertIs(result['child_success'],True);self.assertIs(result['release_sent'],True);self.assertEqual(result['writer_errors'],[])
            self.assertIs(result['drain_observation']['killed'],False)
            self.assertEqual(result['drain_observation_pin'],quiet.pin(quiet.canonical(result['drain_observation'])))
            self.assertIsNone(actor._process);self.assertIsNone(actor._drain);self.assertEqual(quiet.finish(actor),result)
            quiet.close_handle(actor);self.assertIs(result['actual_F'],False)
        self.toy(0,action);self.assertEqual(calls,[])

    def test_18_real_nonzero_toy_preserves_physical_quiet_and_failed_semantics(self):
        def action(process,actor):
            rc,out,err,reason,obs=quiet.drain_child(actor,1.0);quiet.close_handle(actor);result=quiet.finish(actor)
            self.assertEqual(rc,3);self.assertEqual(result['quiet']['child_exit'],3);self.assertIs(result['child_success'],False)
            self.assertIs(result['quiet']['process_handle_closed'],True);self.assertIs(result['transport_success'],False)
            self.assertIs(result['release_sent'],False);self.assertTrue(result['writer_errors'])
            result['writer_errors'].clear();self.assertTrue(quiet.finish(actor)['writer_errors'])
        self.toy(3,action,break_release=True)

    def test_19_opaque_receipts_dummy_threads_and_other_process_objects_are_rejected(self):
        calls=[]
        with patch.object(quiet,'kernel_identity',side_effect=lambda *_:calls.append(True)):
            with self.assertRaises(ValueError):quiet.capture(SimpleNamespace(pid=1),{},[],quiet.pin(b'p'),quiet.pin(b't'),DRAIN_RAW)
        self.assertEqual(calls,[])
        actor=object.__new__(quiet.ParentQuietActor)
        for name,value in dict(_creator=quiet.creator(),_failure=None,_phase='CAPTURED',_writer=None).items():object.__setattr__(actor,name,value)
        quiet._ACTORS[id(actor)]=actor;self.addCleanup(quiet._ACTORS.pop,id(actor),None)
        with self.assertRaisesRegex(ValueError,'actor-owned release writer'):quiet.drain_child(actor,1.0)
        self.assertIsNone(actor._writer)
        with self.assertRaises(ValueError):quiet.finish({})

    def private_drained(self,change):
        actor=object.__new__(quiet.ParentQuietActor);handle=SimpleNamespace(closed=True);pipes=tuple(SimpleNamespace(closed=True) for _ in range(3))
        argv=['ordinary-private'];process=SimpleNamespace(pid=9,_handle=handle,args=argv,stdin=pipes[0],stdout=pipes[1],stderr=pipes[2],returncode=0)
        obs=dict(direct_child_pid=9,pipes_closed=True,reader_threads_terminal=True,killed=False,stdout_truncated=False,
            stderr_truncated=False,reader_errors=[],cleanup=[])
        writer=Thread(target=lambda:None);writer.start();writer.join(.5)
        values=dict(_creator=quiet.creator(),_process=process,_pid=9,_handle=handle,_handle_value=1,_pipes=pipes,_argv=quiet.canonical(argv),
            _identity=quiet.canonical(dict(pid=9,creation=1,image_path=argv[0])),_plan_pin=quiet.pin(b'p'),_transport_pin=quiet.pin(b't'),
            _drain=quiet.function_spec(drain.drain),_writer=writer,_writer_errors=(),_release_raw=b'release',_released=True,
            _raws=(b'{}',b''),_observation=None,_reason=None,_exit=0,_close_attempted=True,_closed=True,_phase='DRAINED',_failure=None,_result=None)
        change(values,obs);values['_observation']=quiet.canonical(obs)
        for name,value in values.items():object.__setattr__(actor,name,value)
        quiet._ACTORS[id(actor)]=actor;self.addCleanup(quiet._ACTORS.pop,id(actor),None)
        return actor

    def test_20_injected_timeout_truncation_reader_and_instance_faults_never_become_quiet(self):
        for field in ('reason','truncate','reader','cleanup','identity','handle','pipes'):
            def change(values,obs):
                if field=='reason':values['_reason']='timeout'
                elif field=='truncate':obs['stdout_truncated']=True
                elif field=='reader':obs['reader_errors']=['injected']
                elif field=='cleanup':obs['cleanup']=['injected']
                elif field=='identity':values['_process'].pid=8
                elif field=='handle':values['_closed']=False
                else:values['_pipes'][0].closed=False
            actor=self.private_drained(change)
            with self.subTest(field=field),self.assertRaises(ValueError) as caught:quiet.finish(actor)
            self.assertIs(actor._failure,caught.exception)
            with self.assertRaises(ValueError) as repeated:quiet.finish(actor)
            self.assertIs(repeated.exception,caught.exception)


if __name__=='__main__':unittest.main()
