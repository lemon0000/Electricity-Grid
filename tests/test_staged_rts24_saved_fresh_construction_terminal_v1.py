"""Synthetic terminal replay and retained cleanup; zero target/native/P1 calls."""
import ast
import base64
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import CodeType,ModuleType,SimpleNamespace
import unittest
from unittest.mock import patch
import zlib

ROOT=Path(__file__).absolute().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


parent=load('_construction_parent38','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v38.py')
oracle=parent.POST
core=load('_construction_core41','experiments/staged_rts24_saved_fresh_pre_entry_lease_v41.py')
engine=load('_construction_lc3','experiments/staged_rts24_saved_fresh_retained_producer_v3.py')
transform=load('_construction_transform','experiments/staged_rts24_saved_fresh_construction_terminal_transform_v1.py')
budget=load('_construction_budget','experiments/staged_rts24_saved_fresh_construction_graph_budget_v1.py')
memory=load('_construction_memory','experiments/staged_rts24_saved_fresh_memory_drain_v1.py')


def exception():
    return dict(type='builtins.ValueError',message='synthetic failure',primary=None,secondary=[],cause=None,group=[],truncated=False)


def terminal_objects():
    namespace=SimpleNamespace(_phase='CONSUMED',_modules=sys.modules,_reference_registered=False,
        module=ModuleType('_synthetic_actual_unregistered'),reference=ModuleType('_synthetic_reference_unregistered'),
        _aliases=('experiments.staged_rts24_saved_fresh_adoption_v1','_saved_F_entry_reference_v1'))
    resource=SimpleNamespace(phase='CLOSED',pending=[None,None])
    owner=SimpleNamespace(_phase='CLOSED',_failure=None,_cleanup_started=True,_namespace=namespace,
        _resource=resource,_boundary=SimpleNamespace(phase='CLOSED'),close_calls=0)
    inputs=SimpleNamespace(_phase='CONSUMED',_successor=owner,_resource=resource)
    owner._source=inputs;resource.owner=owner;namespace._runtime_peer=owner;namespace._inputs=inputs
    return owner,namespace


class LocalRuntimeUnresolved(RuntimeError):
    def __init__(self,owner,primary):self.owner=owner;self.primary=primary;self.secondary=()


def synthetic_close(owner,primary=None):
    owner.close_calls+=1;owner._cleanup_started=True;owner._resource.phase='CLOSED';owner._resource.pending=[None,None]
    owner._boundary.phase='CLOSED';owner._phase='CLOSED' if primary is None else 'UNRESOLVED';owner._failure=primary
    if primary is not None:raise LocalRuntimeUnresolved(owner,primary)


def synthetic_boundary(boundary):return boundary.phase


def synthetic_profile():
    # File names provide the exact selected metadata set; bodies are never executed.
    rows=[]
    for path in parent.source():
        if path.startswith('src/') and path.endswith('.py') or path=='experiments/staged_rts24_saved_fresh_adoption_v1.py':
            name=path[:-3].replace('/','.').removesuffix('.__init__')
            rows.append([name,'module',str(ROOT/path),str(ROOT/path),'synthetic.Loader'])
    return dict(schema='staged_saved_F_B_S_import_observation_v1',authority='DRAFT_NONAUTHORITATIVE',
        modules=sorted(rows),cache=[['synthetic','synthetic.Finder']],paths=['synthetic']*6,finder_types=['synthetic.Finder'],
        machinery_observed=2,machinery_authenticated=2,optional_attempts=1,
        loaded_python_graph_attested=False,registry_contents_verified=False,native_behavior_verified=False)


def compressed(value):
    raw=oracle.canonical(value)
    return dict(encoding='zlib_base64',raw_pin=oracle.pin(raw),data=base64.b64encode(zlib.compress(raw)).decode())


def frames():
    rows=[];clock=0.0;seq=0
    def emit(row):
        nonlocal clock
        clock+=0.01
        if row[0]=='stage':row.append(clock)
        else:row[4]=clock
        rows.append(row)
    def graphs(stage):
        nonlocal seq
        for kind in budget.INTERVALS.get(stage,[]):
            seq+=1;emit(['graph',seq,kind,'enter',None]);emit(['graph',seq,kind,'exit',None,1,1,5])
    def census(reason):
        nonlocal clock
        clock+=0.01
        buckets={key:[0,0.0,0.0] for key in ('identity1','runtime_link','cache','globals_attrs','ownership','image_digest',
            'machinery','entry_total','audit_body_inclusive')}
        frame=dict(schema='staged_saved_F_audit_census_v5',seq=1 if reason=='begin' else 2,reason=reason,limit=2048,
            active=reason=='begin',start_clock=start,snapshot_clock=clock,entered=0,passed=0,rejected=0,observed=0,
            inflight=False,phase=None,last_incomplete=None,buckets=buckets,diagnostic_error_count=0,
            cache_items=0,cache_new=0,machinery_stage=0 if reason=='begin' else 2,installation_seen=1)
        rows.append(['census',frame])
    graphs('<before_loader_ready>');start=clock
    for stage in budget.STAGES:
        emit(['stage',stage])
        if stage=='before_adapter_import':start=clock;census('begin')
        elif stage=='adapter_import_returned':census('import_return_before2048')
        graphs(stage)
    return rows


class ConstructionTerminalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='construction_terminal_');self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name);self.scope=patch.object(parent,'OUT',self.folder);self.scope.start();self.addCleanup(self.scope.stop)
        self.folder.joinpath('import_policy.json').write_bytes(b'{"synthetic_policy":true}')
        # Discovery manifest construction and source/helper hashing are metadata only.
        self.code=b'# synthetic transport; never executed\n';self.plan=parent.manifest('discovery',self.code)
        self.plan['case']='import_discovery';self.plan['startup_profile']=dict(path=str(self.folder/'startup_profile.json'),pin=oracle.pin(b'{}'))
        self.path=self.folder/'probe_import_discovery.plan.json';self.path.write_bytes(oracle.canonical(self.plan))
        self.argv=[str(parent.EXE),'-P','-B','-s','-S','-c',self.code.decode(),'--pre-entry-lease',str(self.path),oracle.pin(self.path.read_bytes())['sha256']]
        self.identity=dict(pid=2345,creation=100,image_path=str(parent.EXE))
        self.r={key:None for key in oracle.PROBE_KEYS};self.r.update({key:False for key in oracle.FLAGS})
        self.r.update(schema='staged_saved_F_project_construction_probe_v2',authority='DRAFT_NONAUTHORITATIVE',case='import_discovery',
            source_epoch=parent.SOURCE_SHA,status='completed',primary=None,secondary=[],failure_phase=None,
            live_at_report=False,runtime_was_live=False,runtime_is_resource_owner=True,old_inputs_successor_matches=True,
            old_namespace_successor_matches=True,namespace_alias_absent=True,dll_directory_close_returned=True,
            runtime_phase_before_close='OBSERVED',runtime_phase='CLOSED',resource_phase='CLOSED',
            source_phase='CONSUMED',inputs_phase='CONSUMED',namespace_phase='CONSUMED',
            close_calls=[1,1],self_handles_closed=True,source_bookends=7,retained_modules=37,boundary_phase='CLOSED',
            graph_calls=43,early_audit_blocked=[],import_profile=compressed(synthetic_profile()),
            kernel_identity=dict(pid=2345,tid=123,process_creation_filetime=100,thread_creation_filetime=101,
                image_path=str(parent.EXE),command_line_sha=oracle.pin(subprocess.list2cmdline(self.argv).encode('utf8'))))
        owner,namespace=terminal_objects();self.r['namespace_terminal']=engine.namespace_terminal_snapshot(owner,namespace)
        graph=dict(schema='staged_saved_F_project_continuity_observation_v1',authority='DRAFT_NONAUTHORITATIVE',
            modules=37,nodes=1,graph_pin=[1,'a'*64],structure_and_identity_stable=True,**{key:False for key in oracle.GRAPH_FALSE})
        self.r['construction_result']=dict(schema='staged_saved_F_unadmitted_project_construction_v1',authority='DRAFT_NONAUTHORITATIVE',
            source_modules=37,loader_execs=36,entry_execs=2,graph=graph,P1_reads=0,admission_present=False,
            **{key:False for key in oracle.CONSTRUCTION_FALSE})
        self.r['guard']=dict(source_open_attempts=49,protected_open_attempts=0,write_attempts=0,process_attempts=0,sentinel=1,
            events=['self_handles_live','source_read_begin','transfer_committed','self_handles_closed'],faults=[])
        br={key:False for key in parent.BOUNDARY_KEYS};br.update(schema='staged_saved_F_successor_import_boundary_report_v1',
            authority='DRAFT_NONAUTHORITATIVE',phase='CLOSED',fault_kind='',machinery_observed_stage=2,
            machinery_authenticated_stage=2,machinery_authentication_pending=False,violations=0,internal_introspection_events=0)
        for key in ('callback_retained','hook_installation_observed','finder_function_mutation_guard_installed',
                'finder_function_metadata_bookend_verified','forced_numpy_SVE_false','source49_bookend_equal','import_boundary_completed'):br[key]=True
        for key in ('optional_Popen_attempts','blocked_optional_attempts','installation_sentinel_observed','audit_handoff_observed'):br[key]=1
        self.r['boundary_report']=br
        self.r['post_metrics']=dict(returned=True,idle_getter_events=1,busy_getter_events=0,
            **{key:[count,0.01,0.01] for key,count in budget.current()[1]['post_return_counts'].items()})
        self.stderr=b''.join(oracle.canonical(row)+b'\n' for row in frames())

    def parsed(self):return oracle.parse(parent,self.stderr)
    def success(self,record=None,parsed=None):return oracle.validate_success(parent,self.r if record is None else record,
        self.parsed() if parsed is None else parsed,self.plan,self.code)

    def test_01_complete_synthetic_terminal_and_graph_DAG(self):
        self.assertEqual(self.success()['mode'],'unadmitted_construction_closed')
        parsed=self.parsed();self.assertEqual(parsed['graph_counts'],dict(namespace=33,adapter=10))
        self.assertEqual(parsed['graph_intervals'],budget.contract()['intervals']);self.assertEqual(len(parsed['graph_frames']),86)
        self.assertEqual(oracle.decode(parent,oracle.canonical(self.r)+b'\n'),self.r)

    def test_02_missing_reordered_duplicate_and_extra_graph(self):
        rows=frames()
        cases=[rows[:-4],rows+[rows[-1]],rows[:]]
        cases[2][0]=['graph',44,'namespace','enter',0.001]
        for rows in cases:
            with self.subTest(rows=len(rows)),self.assertRaises((AssertionError,ValueError)):
                self.success(parsed=oracle.parse(parent,b''.join(oracle.canonical(row)+b'\n' for row in rows)))

    def test_03_wrong_kind_or_null_exit_sizes_reject(self):
        for mode in ('kind','sizes','trailer'):
            rows=frames()
            if mode=='kind':rows[0][2]=rows[1][2]='adapter'
            elif mode=='sizes':rows[1][5:]=[None,None,None]
            raw=b''.join(oracle.canonical(row)+b'\n' for row in rows)+(b'garbage\n' if mode=='trailer' else b'')
            with self.subTest(mode=mode),self.assertRaises((AssertionError,ValueError)):self.success(parsed=oracle.parse(parent,raw))

    def test_04_failure_can_retain_an_incomplete_graph(self):
        raw=oracle.canonical(['graph',1,'namespace','enter',0.1])+b'\n'
        self.assertFalse(oracle.parse(parent,raw)['graph_complete'])

    def test_05_protocol_canonical_duplicate_key_and_NaN(self):
        good=oracle.canonical(self.r)+b'\n'
        for raw in (good+b'\n',good.replace(b'"graph_calls":43',b'"graph_calls":43,"graph_calls":43'),
                good.replace(b'"graph_calls":43',b'"graph_calls":NaN')):
            with self.subTest(raw=raw[:15]),self.assertRaises((AssertionError,ValueError)):oracle.decode(parent,raw)

    def test_06_profile_digest_extra_stream_and_expansion_caps(self):
        self.assertEqual(oracle.profile_data(self.r['import_profile']),synthetic_profile())
        for mode in ('hash','extra','bomb','truncated','boolean_size'):
            value=copy.deepcopy(self.r['import_profile'])
            if mode=='hash':value['raw_pin']['sha256']='0'*64
            elif mode=='boolean_size':value['raw_pin']['bytes']=True
            else:
                packed=base64.b64decode(value['data'])
                packed=packed+b'extra' if mode=='extra' else zlib.compress(b'x'*1048577) if mode=='bomb' else packed[:-1]
                value['data']=base64.b64encode(packed).decode()
            with self.subTest(mode=mode),self.assertRaises((AssertionError,ValueError)):oracle.profile_data(value)

    def test_07_closed_fields_authority_and_counter_types(self):
        for key,value in (('unknown',0),('actual_F',True),('source_bookends',True),('consumer_state',{}),('graph_calls',True)):
            bad=copy.deepcopy(self.r);bad[key]=value
            with self.subTest(key=key),self.assertRaises((AssertionError,ValueError)):oracle.record_shape(parent,bad)

    def test_08_namespace_lineage_alias_and_pending_failure_matrix(self):
        for key,value in (('namespace_same',False),('peer_same',False),('registry_same',False),('actual_aliases',['leak']),
                ('reference_key_absent',False),('pending',[False,True]),('namespace_phase','CLOSED'),('inputs_phase','LIVE')):
            bad=copy.deepcopy(self.r);bad['namespace_terminal'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.success(bad)

    def test_09_count_source_profile_and_guard_order_failures(self):
        for mode in ('finder','bookend','modules','events','early','live'):
            bad=copy.deepcopy(self.r)
            if mode=='finder':bad['post_metrics']['finder_check'][0]=15
            elif mode=='bookend':bad['source_bookends']=6
            elif mode=='modules':
                profile=synthetic_profile();profile['modules'].pop();bad['import_profile']=compressed(profile)
            elif mode=='events':bad['guard']['events'].reverse()
            elif mode=='early':bad['early_audit_blocked']=['blocked']
            else:bad['runtime_was_live']=True
            with self.subTest(mode=mode),self.assertRaises((AssertionError,ValueError)):self.success(bad)

    def test_10_kernel_pid_time_image_and_command_bind(self):
        self.assertTrue(oracle.kernel_match(parent,self.r,self.identity,self.argv))
        for key,value in (('pid',2346),('process_creation_filetime',True),('image_path',str(self.folder/'python.exe')),
                ('command_line_sha',oracle.pin(b'wrong'))):
            bad=copy.deepcopy(self.r);bad['kernel_identity'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):oracle.kernel_match(parent,bad,self.identity,self.argv)

    def test_11_compare_secondary_only_failure_retains_chain(self):
        bad=copy.deepcopy(self.r);bad.update(status='failed',secondary=[exception()],failure_phase='CLOSE')
        with patch.object(oracle,'context',return_value=(b'',self.plan,{'synthetic_context':True})):
            result=oracle.compare(parent,'import_discovery',self.code,oracle.canonical(bad)+b'\n',self.stderr,1,self.identity,self.argv,[])
        self.assertEqual(result['child_record']['secondary'],bad['secondary']);self.assertFalse(result['post_return_terminal_complete'])
        self.assertIsNone(result['child_record']['primary']);self.assertFalse(oracle.terminal_complete(result,None))

    def test_12_success_context_mutation_and_writer_failure_reject(self):
        with patch.object(oracle,'context',side_effect=[(b'',self.plan,{'x':1}),(b'',self.plan,{'x':2})]):
            with self.assertRaisesRegex(ValueError,'context changed'):
                oracle.compare(parent,'import_discovery',self.code,oracle.canonical(self.r)+b'\n',self.stderr,0,self.identity,self.argv,[])
        with self.assertRaisesRegex(ValueError,'writer'):
            oracle.compare(parent,'import_discovery',self.code,b'',b'',1,None,self.argv,['write'])

    def test_13_retained_close_consumed_namespace_is_success(self):
        owner,namespace=terminal_objects();producer=SimpleNamespace(_close_attempted=False,_owner=owner,_consumer_plan=(None,None,namespace))
        owner._boundary_phase=(type(synthetic_boundary),synthetic_boundary.__code__,globals(),None)
        row=(None,None,synthetic_close,synthetic_close.__code__,synthetic_close.__defaults__)
        with patch.multiple(engine,commit=lambda *a,**k:None,reserve_state=lambda *a:None,_RUNTIME_ROWS=(None,None,row)):
            self.assertEqual(engine.cleanup(producer,None),[]);self.assertEqual(engine.cleanup(producer,None),[])
        self.assertEqual(owner.close_calls,1);self.assertEqual(namespace._phase,'CONSUMED')
        self.assertEqual(engine.require_namespace_terminal(engine.namespace_terminal_snapshot(owner,namespace),True)['runtime_phase'],'CLOSED')

    def test_14_retained_primary_close_needs_no_false_secondary(self):
        owner,namespace=terminal_objects();producer=SimpleNamespace(_close_attempted=False,_owner=owner,_consumer_plan=(None,None,namespace))
        owner._boundary_phase=(type(synthetic_boundary),synthetic_boundary.__code__,globals(),None)
        failure=SimpleNamespace(runtime_close=None);primary=LookupError('original')
        row=(None,None,synthetic_close,synthetic_close.__code__,synthetic_close.__defaults__)
        with patch.multiple(engine,commit=lambda *a,**k:None,reserve_state=lambda *a:None,_RUNTIME_ROWS=(None,None,row)):
            self.assertEqual(engine.cleanup(producer,primary,failure),[])
        self.assertIs(failure.runtime_close.primary,primary);self.assertEqual(owner._phase,'UNRESOLVED')
        engine.require_namespace_terminal(engine.namespace_terminal_snapshot(owner,namespace),False)

    def test_15_snapshot_uses_expected_namespace_and_all_aliases(self):
        owner,namespace=terminal_objects();owner._namespace=SimpleNamespace()
        self.assertFalse(engine.namespace_terminal_snapshot(owner,namespace)['namespace_same'])
        owner._namespace=namespace
        with patch.dict(sys.modules,{'_synthetic_alias_leak':namespace.reference}):
            value=engine.namespace_terminal_snapshot(owner,namespace)
            self.assertEqual(value['reference_aliases'],['_synthetic_alias_leak'])
            with self.assertRaises(ValueError):engine.require_namespace_terminal(value,True)

    def test_16_exact_successors_preserve_core_methods_and_43_stop(self):
        self.assertEqual(len(transform.current()[1]['successor_pins']),7)
        def methods(path):
            unit=compile((ROOT/path).read_bytes(),'<same_core>','exec',dont_inherit=True,optimize=0)
            cls=next(code for code in unit.co_consts if type(code) is CodeType and code.co_name=='LocalRuntimeInputs')
            return {code.co_name:code for code in cls.co_consts if type(code) is CodeType}
        self.assertEqual(methods(transform.PAIRS[4][1]),methods(transform.PAIRS[4][2]))
        before=(ROOT/transform.PAIRS[0][1]).read_bytes();after=(ROOT/transform.PAIRS[0][2]).read_bytes()
        self.assertEqual(before.replace(b'not 0 <= count < 40:',b'not 0 <= count < 43:'),after)
        report=budget.current()[1];self.assertEqual(report['producer_without_unadmitted_report'],107)
        self.assertFalse(report['fault_call_budget_complete']);self.assertFalse(report['wall_RSS_storage_admitted'])

    def test_17_manifest_graph_tamper_and_wrong_helper_successor_reject(self):
        plan=copy.deepcopy(self.plan);plan.update(case='discovery',startup_profile=None)
        core.check_plan(core.canonical(plan))
        for mode in ('cap','interval','helper'):
            bad=copy.deepcopy(plan)
            if mode=='cap':bad['graph_contract']['calls']=40
            elif mode=='interval':bad['graph_contract']['intervals']['before_final_runtime_close'].pop()
            else:bad['producer_helpers']['lifecycle']['path']=str(ROOT/transform.PAIRS[1][1])
            with self.subTest(mode=mode),self.assertRaises(ValueError):core.check_plan(core.canonical(bad))

    def test_18_parent_preflight_failure_is_charged_without_spawn(self):
        with patch.object(parent,'transport',side_effect=ValueError('synthetic preflight')),patch.object(parent.subprocess,'Popen') as spawn:
            row=parent.one_case('discovery',5)
        spawn.assert_not_called();self.assertFalse(row['accepted']);self.assertIn('synthetic preflight',row['primary'])
        self.assertGreaterEqual(row['charged_seconds'],0.0);self.assertIsNone(row['transport_pin'])
        self.assertEqual(json.loads((self.folder/'probe_discovery.receipt.json').read_bytes()),row)

    def test_19_parent_manifest_failure_preserves_transport_charge(self):
        with (patch.object(parent,'transport',return_value=self.code),
                patch.object(parent,'manifest',side_effect=ValueError('synthetic manifest')),
                patch.object(parent.subprocess,'Popen') as spawn):
            row=parent.one_case('discovery',5)
        spawn.assert_not_called();self.assertEqual(row['transport_pin'],oracle.pin(self.code));self.assertIsNone(row['plan_pin'])
        self.assertFalse(row['accepted']);self.assertIn('synthetic manifest',row['primary'])

    def test_20_profile_publication_follows_audit_and_is_create_only(self):
        result=dict(child_record=self.r)
        with patch.object(oracle,'audit',return_value=result) as audit:
            publication=oracle.publish_profile(parent,{'case':'import_discovery'})
            audit.assert_called_once_with(parent,{'case':'import_discovery'},published=False)
            self.assertEqual(publication['pin'],self.r['import_profile']['raw_pin'])
            with self.assertRaises(FileExistsError):oracle.publish_profile(parent,{'case':'import_discovery'})
        self.assertEqual((self.folder/'import_profile.json').read_bytes(),oracle.canonical(synthetic_profile()))

    def test_21_rejected_publication_does_not_write_profile(self):
        with patch.object(oracle,'audit',side_effect=ValueError('not quiet')):
            with self.assertRaisesRegex(ValueError,'not quiet'):oracle.publish_profile(parent,{'case':'import_discovery'})
        self.assertFalse((self.folder/'import_profile.json').exists())

    def test_22_startup_rows_and_protected_imports_reject(self):
        profile=dict(schema='staged_saved_F_conditional_startup_profile_v1',
            conditional_tcb_assumption_id='controlled_compute_CPython_3_12_12_windows_vm_stdlib_native_kernel_v1',
            bootstrap_pin=oracle.pin(self.code),environment_sha=oracle.pin(oracle.canonical(self.plan['environment'])),cwd=str(ROOT),
            paths=self.plan['initial_paths'],initial_modules=[['sys','built-in','synthetic.Loader']],module_origins=[['sys','built-in','synthetic.Loader']],
            ordered_import_events=[],disk_file_observations={},native_origin_boundaries=[str(parent.EXE)],initial_runtime_opens=[],
            startup_tcb_authenticated=False,loaded_python_graph_attested=False,native_behavior_verified=False)
        self.assertEqual(oracle.startup_shape(parent,profile,self.plan,self.code),profile)
        for key,value in (('ordered_import_events',[['src.bad',None]]),('module_origins',[['sys']]),
                ('initial_runtime_opens',[str(ROOT/'bad.py')]),('disk_file_observations',{str(ROOT/'bad.py'):oracle.pin(b'x')})):
            bad=copy.deepcopy(profile);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):oracle.startup_shape(parent,bad,self.plan,self.code)

    def test_23_receipt_schema_charge_and_early_terminal_failures(self):
        row={key:None for key in oracle.RECEIPT_FIELDS};row.update(schema='staged_saved_F_construction_parent_receipt_v1',
            authority='DRAFT_NONAUTHORITATIVE',accepted=True,primary=None,cleanup=[],child_exit=0,drain_reason=None,
            charged_seconds=0.1,cap_seconds=5,parent_controller_pid=1234,**{key:False for key in oracle.FLAGS})
        for key,value in (('unknown',1),('charged_seconds',float('inf')),('charged_seconds',-1.0),('cap_seconds',True),
                ('cap_seconds',float('inf')),('child_exit',False),('accepted',False),('parent_process_handle_closed',False)):
            bad=copy.deepcopy(row);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):oracle.audit(parent,bad)

    def test_24_compact_record_preserves_original_compressed_wire(self):
        raw=oracle.canonical(self.r)+b'\n';decoded=oracle.decode(parent,raw)
        self.assertEqual(decoded['import_profile'],self.r['import_profile'])
        self.assertLess(len(raw),131072);self.assertNotIn('modules',decoded['import_profile'])

    def receipt(self):
        stdout=oracle.canonical(self.r)+b'\n';ctx={'synthetic_context':True}
        result=oracle.compare(parent,'import_discovery',self.code,stdout,self.stderr,0,self.identity,self.argv,[])
        guard=memory.initial_guard()
        memory.observe(guard,lambda:{name:{key:1024 for key in memory.METRICS} for name in ('parent','child')})
        guard.update(native_sampler_bound=True,binding=dict(parent_pid=1234,child_pid=2345,child_handle=99,struct_bytes=80),drained_child_pid=2345)
        drain=dict(memory_guard=guard,direct_child_pid=2345,killed=False,pipes_closed=True,reader_threads_terminal=True,
            reader_errors=[],cleanup=[],stdout_truncated=False,stderr_truncated=False)
        row={key:None for key in oracle.RECEIPT_FIELDS}
        row.update(schema='staged_saved_F_construction_parent_receipt_v1',authority='DRAFT_NONAUTHORITATIVE',case='import_discovery',
            accepted=True,primary=None,cleanup=[],child_exit=0,drain_reason=None,charged_seconds=0.1,cap_seconds=5,
            parent_process_handle_closed=True,writer_thread_terminal=True,stdin_closed=True,release_sent=True,writer_errors=[],
            stdout_raw_base64=base64.b64encode(stdout).decode(),stdout_pin=oracle.pin(stdout),
            stderr_raw_base64=base64.b64encode(self.stderr).decode(),stderr_pin=oracle.pin(self.stderr),
            plan_pin=oracle.pin(self.path.read_bytes()),expected_manifest_pin=oracle.pin(self.path.read_bytes()),
            transport_pin=oracle.pin(self.code),parent_kernel_identity=self.identity,result=result,context_before=ctx,context_after=ctx,
            bounded_drain=drain,parent_controller_pid=1234,memory_observation_source='last_live_memory_guard',
            memory_observation=dict(peak_working_set_bytes=1024,error=None),**{key:False for key in oracle.FLAGS})
        return row

    def test_25_quiet_receipt_replays_raw_streams_then_publishes(self):
        with (patch.object(oracle,'context',return_value=(b'',self.plan,{'synthetic_context':True})),
                patch.object(parent,'transport',return_value=self.code)):
            row=self.receipt();self.assertEqual(oracle.audit(parent,row,published=False),row['result'])
            row['profile_publication']=oracle.publish_profile(parent,row)
            self.assertEqual(oracle.audit(parent,row),row['result'])
            (self.folder/'import_profile.json').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'published profile'):oracle.audit(parent,row)

    def test_26_quiet_receipt_stream_pid_memory_and_context_tamper(self):
        with (patch.object(oracle,'context',return_value=(b'',self.plan,{'synthetic_context':True})),
                patch.object(parent,'transport',return_value=self.code)):
            row=self.receipt()
            for mode in ('stream','pid','memory','context','thread','killed'):
                bad=copy.deepcopy(row)
                if mode=='stream':bad['stdout_raw_base64']=base64.b64encode(b'changed').decode()
                elif mode=='pid':bad['bounded_drain']['direct_child_pid']=2346
                elif mode=='memory':bad['bounded_drain']['memory_guard']['error']='failed'
                elif mode=='context':bad['context_before']={'synthetic_context':False}
                elif mode=='thread':bad['writer_thread_terminal']=False
                else:bad['bounded_drain']['killed']=True
                with self.subTest(mode=mode),self.assertRaises((AssertionError,ValueError)):oracle.audit(parent,bad,published=False)

    def test_27_late_cap_preserves_rejected_profile_and_releases_target(self):
        row=dict(case='import_discovery',accepted=True,primary=None,cleanup=[],profile_publication=None)
        ticks=iter((2.0,2.1))
        with patch.object(oracle,'audit',return_value=dict(child_record=self.r)):
            oracle.finalize_profile(parent,row,0.0,1.0,lambda:next(ticks))
            self.assertFalse(row['accepted']);self.assertEqual(row['primary'],'parent_phase_cap_exceeded')
            self.assertEqual(row['charged_seconds'],2.1);self.assertEqual(row['cleanup'],[])
            self.assertFalse((self.folder/'import_profile.json').exists())
            target=self.folder/'import_profile.rejected.json'
            self.assertEqual(target.read_bytes(),oracle.canonical(synthetic_profile()))
            self.assertFalse(row['profile_publication']['adopted'])
            # The rejected bytes survive a separate synthetic publication.
            good=dict(case='import_discovery',accepted=True,primary=None,cleanup=[],profile_publication=None)
            oracle.finalize_profile(parent,good,0.0,1.0,lambda:0.5)
        self.assertTrue(good['accepted']);self.assertEqual(good['charged_seconds'],0.5)
        self.assertTrue(target.exists());self.assertEqual((self.folder/'import_profile.json').read_bytes(),target.read_bytes())

    def test_28_publication_readback_failure_retires_only_new_file(self):
        original=Path.read_bytes
        def read(path):
            if path==self.folder/'import_profile.json':raise OSError('synthetic readback')
            return original(path)
        row=dict(case='import_discovery',accepted=True,primary=None,cleanup=[],profile_publication=None)
        with (patch.object(oracle,'audit',return_value=dict(child_record=self.r)),patch.object(Path,'read_bytes',read)):
            oracle.finalize_profile(parent,row,0.0,1.0,lambda:0.5)
        self.assertFalse(row['accepted']);self.assertIn('synthetic readback',row['primary']);self.assertEqual(row['cleanup'],[])
        self.assertFalse((self.folder/'import_profile.json').exists());self.assertTrue((self.folder/'import_profile.rejected.json').exists())

    def test_29_foreign_profile_identity_or_existing_archive_is_preserved(self):
        path=self.folder/'import_profile.json';path.write_bytes(b'foreign');info=path.stat()
        with self.assertRaisesRegex(ValueError,'identity changed'):oracle.retire_profile(parent,[(path,info.st_dev,info.st_ino+1)])
        self.assertEqual(path.read_bytes(),b'foreign')
        target=self.folder/'import_profile.rejected.json';target.write_bytes(b'frozen failure')
        with self.assertRaisesRegex(ValueError,'create-only'):oracle.retire_profile(parent,[(path,info.st_dev,info.st_ino)])
        self.assertEqual(path.read_bytes(),b'foreign');self.assertEqual(target.read_bytes(),b'frozen failure')


if __name__=='__main__':unittest.main()
