"""Parent40: two fixed stdlib children and private failure/data fixtures only."""
import base64
import copy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import FunctionType,ModuleType,SimpleNamespace
import unittest
import zlib

ROOT=Path(__file__).absolute().parents[1]
PARENT_PATH=ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v40.py'
VALID_PATH=ROOT/'experiments/staged_rts24_saved_fresh_complete_bootstrap_validation_v1.py'
QUIET_PATH=ROOT/'experiments/staged_rts24_saved_fresh_parent_quiet_actor_v2.py'

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

parent=load(PARENT_PATH,'_complete_parent_source')
validation=load(VALID_PATH,'_complete_validation_source')
old=load(ROOT/'tests/test_staged_rts24_saved_fresh_producer_export_v2.py','_complete_parent_export_fixture')
CANONICAL=parent.canonical
PIN=parent.pin
FALSE=parent.flags()
STATE={'started':False,'error':None}
CONTRACT=dict(calls=1,intervals={'<before_loader_ready>':['namespace']},
    metrics=dict(authenticate=1,finder_check=16,adapter_check=9,profile=2),source_bookends=7)
CONTRACTS=(('discovery',()),('import_discovery',CONTRACT),('producer',CONTRACT))

def private_context(raw,code,argv,held=None,profile_dependency=None):
    return dict(schema='ordinary_private_parent_context',manifest_pin=PIN(raw),transport_pin=PIN(code),argv_pin=PIN(CANONICAL(argv)))

def private_parent(name):
    m=load(PARENT_PATH,name)
    m.EXE=Path(sys.executable)
    m.input_context=private_context
    original_dependencies=m.dependencies
    def fixture_dependencies():
        held=original_dependencies()
        v=load(VALID_PATH,name+'_private_validation')
        v._EXACT_CONTRACTS=copy.deepcopy(CONTRACTS)
        if STATE.get('registration') is not None:v._PROFILE_ACCEPTED_ANCHOR=(PIN(STATE['registration'])['sha256'],)
        return tuple((key,m.program(vars(v)) if key=='validation' else value) for key,value in held)
    m.dependencies=fixture_dependencies
    m.profile_dependency_for=lambda held,kind:STATE['profile_dependency']
    return m

def census(seq,reason,clock,start,passed,observed,active,stage):
    row=dict(schema='staged_saved_F_audit_census_v5',seq=seq,reason=reason,limit=2048,active=active,
        start_clock=start,snapshot_clock=clock,entered=passed,passed=passed,rejected=0,observed=observed,
        inflight=False,phase=None,last_incomplete=None,buckets={name:[passed,.01*passed,.005*passed]
            for name in ('identity1','runtime_link','cache','globals_attrs','ownership','image_digest','machinery','entry_total','audit_body_inclusive')},
        diagnostic_error_count=0,cache_items=passed,cache_new=passed,machinery_stage=stage,installation_seen=1)
    return row

def trace():
    rows=[['graph',1,'namespace','enter',1.],['graph',1,'namespace','exit',1.1,1,1,1]]
    for index,name in enumerate(validation.STAGES):
        clock=2.+10.*index;rows.append(['stage',name,clock])
        if name=='before_adapter_import':
            rows.extend([['census',census(1,'begin',clock+.1,clock+.1,0,0,True,0)],
                ['census',census(2,'progress',clock+.2,clock+.1,1,0,True,1)]])
        if name=='adapter_import_returned':rows.append(['census',census(3,'import_return_before2048',clock+.1,12.1,1,1,False,2)])
    return b''.join(CANONICAL(row)+b'\n' for row in rows)

def plan(case,code,nonce):
    refs=dict(startup_profile=dict(path=str(parent.OUT/'startup_profile.json'),pin=PIN(b'ordinary-startup')))
    if case=='producer':refs['import_profile']=dict(path=str(parent.OUT/'import_profile.json'),pin=PIN(STATE['profile_raw']))
    else:refs['import_profile']=None
    return dict(schema='staged_saved_F_complete_bootstrap_manifest_v1',authority='DRAFT_NONAUTHORITATIVE',case=case,nonce=nonce,
        source_pins=old.legacy.SOURCE_PINS,source_epoch=parent.SOURCE_SHA,bootstrap_pin=PIN(code),executable_pin=PIN(b'private-exe'),
        python='ordinary-private-python',environment={},cwd=str(ROOT),initial_paths=[],selected_runtime_file_observations={},
        startup_absent=[],namespace_helper={},import_helper={},import_policy={},producer_helpers={},graph_contract={},**refs)

def import_profile():
    wanted={name[:-3].replace('/','.').removesuffix('.__init__'):str(ROOT/name)
        for name in old.legacy.SOURCE_PINS if name.startswith('src/') and name.endswith('.py')
            or name=='experiments/staged_rts24_saved_fresh_adoption_v1.py'}
    return dict(schema='staged_saved_F_B_S_import_observation_v1',authority='DRAFT_NONAUTHORITATIVE',
        modules=[[name,'module',path,None,'ordinary.Loader'] for name,path in sorted(wanted.items())],
        cache=[['ordinary-cache','ordinary.Finder']],paths=['ordinary']*6,finder_types=['ordinary.Finder'],
        machinery_observed=2,machinery_authenticated=2,optional_attempts=1,
        loaded_python_graph_attested=False,registry_contents_verified=False,native_behavior_verified=False)

def fixture_producer():
    f=old.ExportLifecycleTests('test_55_coordinator_full_private_chain_and_quiet_data_replay');f.setUp()
    try:f.setup_coordinator();return f.complete()
    finally:f.tearDown()

def payload(case):
    ns={key:True for key in validation.NAMESPACE_KEYS}
    ns.update(schema='staged_saved_F_namespace_terminal_observation_v1',authority='DRAFT_NONAUTHORITATIVE',
        runtime_phase='CLOSED',resource_phase='CLOSED',namespace_phase='CONSUMED',inputs_phase='CONSUMED',
        pending=[False,False],actual_aliases=[],reference_aliases=[],reference_registered=False)
    counters={key:0 for key in ('selected','protected','allowed','writes','processes','mutations','construction_reads','runtime_reads','outside_reads')}
    permission=dict(schema='staged_saved_F_P1_permission_observation_v1',authority='DRAFT_NONAUTHORITATIVE',
        issuer_phase='DISABLED',guard_phase='CLOSED',installed=True,counters=counters,faults=[],admission_present=False,
        **{key:False for key in ('external_permission_verified','full_P1_content_verified','independent_root_verified','role_bootstrap',
        'permit_issued','run_authority','F_launch_admitted','actual_F','resource_admission','scientific_evidence_adopted','formal_result')})
    terminal=dict(runtime_phase='CLOSED',resource_phase='CLOSED',consumer_state=None,close_calls=[1,1],pending=[False,False],
        namespace_phase='CONSUMED',cleanup_started=True)
    construction=dict(schema='staged_saved_F_unadmitted_project_construction_v1',authority='DRAFT_NONAUTHORITATIVE',
        source_modules=37,loader_execs=36,entry_execs=2,P1_reads=0,admission_present=False,
        graph=dict(schema='staged_saved_F_project_continuity_observation_v1',authority='DRAFT_NONAUTHORITATIVE',
            modules=37,nodes=1,graph_pin=[1,'0'*64],structure_and_identity_stable=True,**{key:False for key in validation.GRAPH_FALSE}),
        **{key:False for key in validation.CONSTRUCTION_FALSE})
    complete=fixture_producer() if case=='producer' else None
    if complete is not None:terminal=complete['terminal'];permission=complete['permission'];construction=None
    actor=dict(schema='staged_saved_F_bootstrap_actor_observation_v1',authority='DRAFT_NONAUTHORITATIVE',phase='CLOSED',mode=case,
        terminal=terminal,permission=permission,secondary_count=0,**{key:False for key in validation.ACTOR_FALSE})
    boundary={key:False for key in validation.BOUNDARY_KEYS}
    boundary.update(schema='staged_saved_F_successor_import_boundary_report_v1',authority='DRAFT_NONAUTHORITATIVE',phase='CLOSED',
        fault_kind='',machinery_observed_stage=2,machinery_authenticated_stage=2,violations=0,internal_introspection_events=1,
        **{key:1 for key in ('optional_Popen_attempts','blocked_optional_attempts','installation_sentinel_observed','audit_handoff_observed')},
        **{key:True for key in ('callback_retained','hook_installation_observed','finder_function_mutation_guard_installed',
            'finder_function_metadata_bookend_verified','forced_numpy_SVE_false','source49_bookend_equal','import_boundary_completed')})
    profile_raw=CANONICAL(import_profile())
    r={key:None for key in validation.PROBE_KEYS}
    r.update(schema='staged_saved_F_complete_bootstrap_probe_v1',authority='DRAFT_NONAUTHORITATIVE',case=case,status='completed',
        primary=None,secondary=[],failure_phase=None,source_epoch=parent.SOURCE_SHA,dll_directory_close_returned=True,
        runtime_phase_before_close='LIVE' if case=='producer' else 'OBSERVED',
        post_metrics=dict(returned=True,idle_getter_events=1,busy_getter_events=0,
            **{key:[count,0.,0.] for key,count in CONTRACT['metrics'].items()}),
        construction_result=construction,bootstrap_actor=actor,producer_result=complete,namespace_terminal=ns,
        permission_observation=permission,consumer_state='CONSUMED' if case=='producer' else None,graph_calls=1,
        runtime_was_live=case=='producer',runtime_phase='CLOSED',resource_phase='CLOSED',self_handles_closed=True,close_calls=[1,1],
        source_phase='CONSUMED',inputs_phase='CONSUMED',namespace_phase='CONSUMED',runtime_is_resource_owner=True,
        old_inputs_successor_matches=True,old_namespace_successor_matches=True,boundary_phase='CLOSED',boundary_report=boundary,
        retained_modules=37,source_bookends=7,namespace_alias_absent=True,
        import_profile=dict(encoding='zlib_base64',raw_pin=PIN(profile_raw),data=base64.b64encode(zlib.compress(profile_raw)).decode('ascii')),
        guard=dict(source_open_attempts=1,protected_open_attempts=0,write_attempts=0,process_attempts=0,faults=[],sentinel=1,
            events=['self_handles_live','source_read_begin','transfer_committed','self_handles_closed']),
        early_audit_blocked=[],live_at_report=False,**{key:False for key in validation.FLAGS})
    return r

TOY=r"""
import ctypes as C
from ctypes import wintypes as W
import json,os,sys,subprocess,time
from hashlib import sha256
from pathlib import Path
release=sys.stdin.buffer.read()
expected=b'SAVED_PRE_ENTRY_V1:'+sys.argv[3].encode('ascii')+b'\n'
if release!=expected:raise SystemExit(3)
time.sleep(.12)
container=json.loads(Path(sys.argv[2]).read_bytes());record=container['record']
kernel=C.WinDLL('kernel32',use_last_error=True)
kernel.GetCurrentProcess.restype=W.HANDLE;kernel.GetCurrentThread.restype=W.HANDLE
for name in ('GetProcessTimes','GetThreadTimes'):
    fn=getattr(kernel,name);fn.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;fn.restype=W.BOOL
values=[W.FILETIME() for _ in range(4)];other=[W.FILETIME() for _ in range(4)]
assert kernel.GetProcessTimes(kernel.GetCurrentProcess(),*[C.byref(v) for v in values])
assert kernel.GetThreadTimes(kernel.GetCurrentThread(),*[C.byref(v) for v in other])
kernel.GetCommandLineW.restype=W.LPWSTR
record['kernel_identity']=dict(pid=os.getpid(),tid=kernel.GetCurrentThreadId(),
    process_creation_filetime=values[0].dwLowDateTime|values[0].dwHighDateTime<<32,
    thread_creation_filetime=other[0].dwLowDateTime|other[0].dwHighDateTime<<32,image_path=sys.executable,
    command_line_sha=dict(bytes=len(kernel.GetCommandLineW().encode('utf8')),
        sha256=sha256(kernel.GetCommandLineW().encode('utf8')).hexdigest()))
sys.stderr.buffer.write(bytes.fromhex(container['stderr_hex']));sys.stderr.buffer.flush()
sys.stdout.buffer.write(json.dumps(record,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')+b'\n')
"""

def run_toy(case,nonce):
    code=TOY.encode('utf8');raw=CANONICAL(plan(case,code,nonce))
    with tempfile.TemporaryDirectory(prefix='saved-complete-parent-') as temporary:
        path=Path(temporary)/'ordinary_payload.json'
        dependency_path=Path(temporary)/'ordinary_profile_dependency.json'
        dependency_path.write_bytes(CANONICAL({key:base64.b64encode(value).decode('ascii')
            for key,value in STATE.get('profile_dependency',{}).items()}))
        # Only this private source copy changes its plan/context fixture and exact
        # synthetic constants. All production source files remain byte-for-byte.
        extra="\nimport sys\nEXE=Path(sys.executable)\n"
        extra+="\ndef input_context(raw,code,argv,held=None,profile_dependency=None):\n    return dict(schema='ordinary_private_parent_context',manifest_pin=pin(raw),transport_pin=pin(code),argv_pin=pin(canonical(argv)))\n"
        extra+="\n_ordinary_dependencies=dependencies\n"
        extra+="\ndef dependencies():\n    held=_ordinary_dependencies()\n    v=source_module('validation')\n    v._EXACT_CONTRACTS="+repr(CONTRACTS)+"\n"
        anchor=None if STATE.get('registration') is None else (PIN(STATE['registration'])['sha256'],)
        extra+="    v._PROFILE_ACCEPTED_ANCHOR="+repr(anchor)+"\n"
        extra+="    return tuple((key,program(vars(v)) if key=='validation' else value) for key,value in held)\n"
        extra+="\ndef profile_dependency_for(held,kind):\n    raw=Path("+repr(str(dependency_path))+").read_bytes()\n    return {key:base64.b64decode(value,validate=True) for key,value in json.loads(raw).items()}\n"
        private_raw=PARENT_PATH.read_bytes()+extra.encode('utf8')
        spec=parent.source_dispatch(private_raw,PIN(private_raw));namespace=spec[2][0][2][0]
        def invoke(operation,args):return FunctionType(spec[0],spec[1])(spec[2],operation,args)
        def dispatch(actor,operation,args=()):
            return invoke(operation,(actor,*args))
        m=SimpleNamespace(capture=lambda process,raw,code,argv:invoke('capture',(process,raw,code,argv)),
            dispatch=dispatch,_PARENTS=namespace['_PARENTS'],parent_view=namespace['parent_view'],
            call=parent.call,get_program=parent.get_program)
        path.write_bytes(CANONICAL(dict(record=payload(case),stderr_hex=trace().hex())))
        argv=[sys.executable,'-P','-B','-s','-S','-c',TOY,'--pre-entry-lease',str(path),PIN(raw)['sha256']]
        process=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        actor=None
        try:
            actor=m.capture(process,raw,code,argv)
            q=actor._quiet;held=actor._held;view=m.parent_view(held)
            result=m.dispatch(actor,'run',(1.,))
            if result.get('accepted') is not True:raise AssertionError('ordinary private parent failed: '+str(result)[:3000])
            observation=m.dispatch(actor,'observation',())
            assert observation==result and actor._phase=='RETIRED' and id(actor) not in m._PARENTS
            registry=dict(m.get_program(held,'quiet')[0])['_ACTORS']
            assert id(q) not in registry and q._phase=='RETIRED'
            assert actor._process is actor._held is actor._quiet is actor._program is None
            return dict(module=m,view=view,held=held,actor=actor,quiet_actor=q,value=result,raw=CANONICAL(result),
                manifest=raw,code=code,argv=argv,record=json.loads(base64.b64decode(result['receipt']['stdout_raw_base64'])),
                stdout=base64.b64decode(result['receipt']['stdout_raw_base64']),stderr=base64.b64decode(result['receipt']['stderr_raw_base64']),
                quiet=result['receipt']['quiet_receipt'])
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=1.)
            for stream in (process.stdin,process.stdout,process.stderr):
                if not stream.closed:stream.close()
            if not process._handle.closed:process._handle.Close()

def ensure():
    if STATE['started']:
        if STATE['error'] is not None:raise STATE['error']
        return STATE
    STATE['started']=True
    try:
        STATE['import']=run_toy('import_discovery','1'*32)
        item=STATE['import'];STATE['profile_raw']=CANONICAL(import_profile())
        reg=CANONICAL(dict(schema='staged_saved_F_complete_parent_registration_v1',authority='DRAFT_NONAUTHORITATIVE',accepted=True,
            transport_pin=PIN(item['code']),source_pins_pin=PIN(CANONICAL(old.legacy.SOURCE_PINS)),
            helper_pins_pin=PIN(CANONICAL({})),**FALSE))
        STATE['registration']=reg
        admission=CANONICAL(dict(schema='staged_saved_F_independent_import_profile_admission_v1',authority='DRAFT_NONAUTHORITATIVE',
            accepted=True,receipt_pin=PIN(item['raw']),profile_pin=PIN(STATE['profile_raw']),manifest_pin=PIN(item['manifest']),
            registration_pin=PIN(reg),transport_pin=PIN(item['code']),environment_pin=PIN(CANONICAL({})),
            source_pins_pin=PIN(CANONICAL(old.legacy.SOURCE_PINS)),helper_pins_pin=PIN(CANONICAL({})),**FALSE))
        STATE['profile_dependency']=dict(profile_raw=STATE['profile_raw'],receipt_raw=item['raw'],manifest_raw=item['manifest'],
            admission_raw=admission,registration_raw=reg)
        STATE['producer']=run_toy('producer','2'*32)
        return STATE
    except BaseException as error:STATE['error']=error;raise

def replay(which='producer',change=None,original=False):
    data=ensure()[which];value=copy.deepcopy(data['record']);quiet=copy.deepcopy(data['quiet'])
    if change is not None:change(value,quiet)
    stdout=CANONICAL(value)+b'\n'
    # Keep original transport observation unless a test explicitly inspects a later data layer.
    if change is not None:quiet['stdout_pin']=PIN(stdout)
    view=data['view']
    if original:return validation.replay(view,data['manifest'],data['code'],data['argv'],stdout,data['stderr'],quiet,
        profile_dependency=STATE.get('profile_dependency'))
    return data['module'].call(data['module'].get_program(data['held'],'validation'),'replay',view,data['manifest'],
        data['code'],data['argv'],stdout,data['stderr'],quiet,profile_dependency=STATE.get('profile_dependency'))

def startup_relation_fixture(test):
    data=ensure()['import'];m=data['module'];view=data['view'];code=data['code']
    reference=json.loads(data['manifest']);reference.update(case='discovery',nonce='0'*32,startup_profile=None)
    reference_raw=CANONICAL(reference)
    profile=dict(schema='staged_saved_F_conditional_startup_profile_v1',
        conditional_tcb_assumption_id='controlled_compute_CPython_3_12_12_windows_vm_stdlib_native_kernel_v1',
        bootstrap_pin=PIN(code),environment_sha=PIN(CANONICAL(reference['environment'])),cwd=str(ROOT),paths=reference['initial_paths'],
        initial_modules=[['builtins',None,'ordinary.Loader']],ordered_import_events=[],
        module_origins=[['builtins',None,'ordinary.Loader']],disk_file_observations={},
        native_origin_boundaries=[str(parent.RUNTIME/'python.exe')],initial_runtime_opens=[],
        startup_tcb_authenticated=False,loaded_python_graph_attested=False,native_behavior_verified=False)
    profile_raw=CANONICAL(profile)
    record=copy.deepcopy(data['record'])
    for key in ('runtime_phase_before_close','runtime_phase','resource_phase','inputs_phase','namespace_phase','source_phase',
            'kernel_identity','close_calls','self_handles_closed','boundary_phase','boundary_report','post_metrics','graph_calls',
            'construction_result','namespace_terminal','permission_observation','bootstrap_actor','producer_result','consumer_state','guard','import_profile'):
        record[key]=None
    record.update(case='discovery',status='discovery_only',startup_profile=profile,source_bookends=0,retained_modules=0,
        runtime_was_live=False,runtime_is_resource_owner=False,old_inputs_successor_matches=False,old_namespace_successor_matches=False)
    stdout=CANONICAL(record)+b'\n';argv=list(data['argv']);argv[-1]=PIN(reference_raw)['sha256']
    quiet=copy.deepcopy(data['quiet']);quiet.update(plan_pin=PIN(reference_raw),argv_pin=PIN(CANONICAL(argv)),
        stdout_pin=PIN(stdout),stderr_pin=PIN(b''),release_pin=PIN(b'SAVED_PRE_ENTRY_V1:'+argv[-1].encode('ascii')+b'\n'))
    result=validation.replay(view,reference_raw,code,argv,stdout,b'',quiet)
    context=private_context(reference_raw,code,argv)
    row=dict(schema='staged_saved_F_complete_parent_receipt_v1',authority='DRAFT_NONAUTHORITATIVE',case='discovery',accepted=True,
        manifest_raw_base64=base64.b64encode(reference_raw).decode('ascii'),argv=argv,
        stdout_raw_base64=base64.b64encode(stdout).decode('ascii'),stderr_raw_base64='',quiet_receipt=quiet,
        result=result,primary=None,secondary=[],context_before=context,context_after=context,parent_controller_pid=os.getpid(),**FALSE)
    row_raw=CANONICAL(row)
    evidence=CANONICAL(dict(schema='staged_saved_F_parent_retirement_record_v1',authority='DRAFT_NONAUTHORITATIVE',
        quiet_snapshot_pin=PIN(CANONICAL(quiet)),parent_result_pin=PIN(row_raw),accepted=True,**FALSE))
    receipt=CANONICAL(dict(schema='staged_saved_F_complete_parent_terminal_v1',authority='DRAFT_NONAUTHORITATIVE',accepted=True,
        receipt=row,receipt_pin=PIN(row_raw),retirement=dict(schema='staged_saved_F_parent_actor_retirement_v1',
            authority='DRAFT_NONAUTHORITATIVE',exact_registry_row_retired=True,terminal_snapshot_pin=PIN(CANONICAL(quiet)),
            evidence_pin=PIN(evidence),**FALSE),retirement_evidence_base64=base64.b64encode(evidence).decode('ascii'),
        terminal_parent_phase='RETIRED',**FALSE))
    target=json.loads(data['manifest']);target['startup_profile']=dict(path=str(parent.OUT/'startup_profile.json'),pin=PIN(profile_raw))
    target_raw=CANONICAL(target);reg=STATE['registration']
    admission=CANONICAL(dict(schema='staged_saved_F_independent_startup_profile_admission_v1',authority='DRAFT_NONAUTHORITATIVE',
        accepted=True,receipt_pin=PIN(receipt),profile_pin=PIN(profile_raw),manifest_pin=PIN(reference_raw),registration_pin=PIN(reg),
        transport_pin=PIN(code),environment_pin=PIN(CANONICAL({})),source_pins_pin=PIN(CANONICAL(old.legacy.SOURCE_PINS)),
        helper_pins_pin=PIN(CANONICAL({})),**FALSE))
    dependency=dict(profile_raw=profile_raw,receipt_raw=receipt,manifest_raw=reference_raw,admission_raw=admission,registration_raw=reg)
    with test.assertRaisesRegex(ValueError,'registration anchor remains open'):
        validation.startup_relation(view,target_raw,code,dependency)
    # The already frozen first toy has no profile anchor because it needed none.
    v=load(VALID_PATH,'_ordinary_startup_relation_fixture');v._PROFILE_ACCEPTED_ANCHOR=(PIN(reg)['sha256'],)
    held=m.get_program(data['held'],'validation')
    proof=parent.program(vars(v))
    related=parent.call(proof,'startup_relation',view,target_raw,code,dependency)
    test.assertEqual(related['profile_pin'],PIN(profile_raw))
    changed=copy.deepcopy(dependency);changed['profile_raw']=CANONICAL(dict(profile,paths=['wrong']))
    with test.assertRaises(ValueError):parent.call(proof,'startup_relation',view,target_raw,code,changed)

class CompleteParentTests(unittest.TestCase):
    def test_01_two_real_toys_complete_private_parent_data_and_registry_lifecycle(self):
        state=ensure()
        for which in ('import','producer'):
            data=state[which]
            self.assertIs(data['value']['accepted'],True)
            self.assertIs(data['value']['actual_F'],False)
            self.assertIsNone(data['actor']._process);self.assertIsNone(data['quiet_actor']._process)
            saved=data['module'].call(data['module'].get_program(data['held'],'validation'),'audit_saved',
                data['view'],data['raw'],data['code'],profile_dependency=STATE.get('profile_dependency') if which=='producer' else None)
            self.assertIs(saved['accepted'],True)
        self.assertEqual(state['producer']['value']['receipt']['result']['producer_replay']['physical_parent_P1_reads'],0)

    def test_02_default_exact_graph_and_external_profile_anchor_stay_closed(self):
        ensure();result=replay('import',original=True)
        self.assertIs(result['accepted'],False);self.assertEqual(result['remaining_gate'],'exact_complete_graph_contract_unresolved')
        self.assertEqual(validation._EXACT_CONTRACTS,(('discovery',()),('import_discovery',None),('producer',None)))
        self.assertIsNone(validation._PROFILE_ACCEPTED_ANCHOR)

    def test_03_saved_terminal_pin_retirement_and_nested_copy_tampering_reject(self):
        data=ensure()['import']
        for field in ('receipt_pin','retirement','retirement_evidence_base64','terminal_parent_phase'):
            value=copy.deepcopy(data['value'])
            if field=='receipt_pin':value[field]['sha256']='0'*64
            elif field=='retirement':value[field]['exact_registry_row_retired']=False
            elif field=='retirement_evidence_base64':value[field]='e30='
            else:value[field]='UNRESOLVED'
            with self.subTest(field=field),self.assertRaises((ValueError,KeyError,TypeError)):
                validation.open_saved_receipt(CANONICAL(value))
        altered=data['module'].dispatch(data['actor'],'observation',());altered['receipt']['quiet_receipt']['writer_errors'].append('caller')
        self.assertEqual(data['module'].dispatch(data['actor'],'observation',()),data['value'])

    def test_04_retained_stream_manifest_transport_argv_and_release_pins_are_exact(self):
        data=ensure()['import']
        for field in ('plan_pin','transport_pin','argv_pin','stdout_pin','stderr_pin','release_pin'):
            quiet=copy.deepcopy(data['quiet']);quiet[field]['sha256']='0'*64
            with self.subTest(field=field),self.assertRaises(ValueError):
                validation.quiet_shape(quiet,data['manifest'],data['code'],data['argv'],data['stdout'],data['stderr'])

    def test_05_nonzero_child_and_writer_failure_never_become_producer_success(self):
        data=ensure()['import']
        for field in ('child_success','transport_success','release_sent','writer_errors','quiet'):
            q=copy.deepcopy(data['quiet'])
            if field=='quiet':q[field]['child_exit']=3
            elif field=='writer_errors':q[field]=['BrokenPipeError']
            else:q[field]=False
            with self.subTest(field=field),self.assertRaises(ValueError):
                validation.quiet_shape(q,data['manifest'],data['code'],data['argv'],data['stdout'],data['stderr'])

    def test_06_actor_probe_permission_and_terminal_must_match(self):
        for key in ('terminal','permission'):
            def change(record,q):
                record['bootstrap_actor'][key]=copy.deepcopy(record['bootstrap_actor'][key])
                if key=='terminal':record['bootstrap_actor'][key]['consumer_state']='PREPARED'
                else:record['bootstrap_actor'][key]['issuer_phase']='DISABLED'
            with self.subTest(key=key),self.assertRaises(ValueError):replay(change=change)

    def test_07_producer_result_cannot_be_supplied_outside_original_child_record(self):
        def change(record,q):record['producer_result']['terminal']['close_calls']=[0,0]
        with self.assertRaises(ValueError):replay(change=change)
        def changed_permission(record,q):record['producer_result']['permission']['counters']['writes']=1
        with self.assertRaises(ValueError):replay(change=changed_permission)

    def test_08_packet_compression_and_false_gate_changes_reject(self):
        def change(record,q):record['producer_result']['producer']['packet']['data']+='eA=='
        with self.assertRaises(ValueError):replay(change=change)
        def gate(record,q):record['producer_result']['actual_F']=True
        with self.assertRaises(ValueError):replay(change=gate)

    def test_09_namespace_owner_and_exact_handle_types_reject(self):
        for key in ('resource_owner_same','pending'):
            def change(record,q):
                record['namespace_terminal'][key]=False if key=='resource_owner_same' else [0,False]
            with self.subTest(key=key),self.assertRaises(ValueError):replay('import',change)

    def test_10_live_memory_guard_requires_same_creating_parent_and_child(self):
        for role in ('parent_pid','child_pid'):
            def change(record,q):
                q['drain_observation']['memory_guard']['binding'][role]+=1
                q['drain_observation_pin']=PIN(CANONICAL(q['drain_observation']))
            with self.subTest(role=role),self.assertRaises(ValueError):replay('import',change)

    def test_11_graph_order_duplicates_incomplete_pairs_and_stop_are_rejected(self):
        data=ensure()['import']
        variants=[data['stderr']+b'["graph",257,"namespace","enter",999.0]\n',
            data['stderr'].replace(b'["graph",1,"namespace","exit"',b'["graph",2,"namespace","exit"',1),
            data['stderr']+CANONICAL(['stage','loader_ready',999.])+b'\n']
        for raw in variants:
            with self.assertRaises((ValueError,AssertionError)):validation.parse_stderr(raw)

    def test_12_profile_independence_artifact_set_and_all_pins_are_required(self):
        data=ensure()['producer'];m=data['module'];held=m.get_program(data['held'],'validation')
        for field in ('profile_raw','receipt_raw','manifest_raw','admission_raw','registration_raw'):
            dependency=copy.deepcopy(STATE['profile_dependency']);dependency[field]+=b' '
            with self.subTest(field=field),self.assertRaises((ValueError,AssertionError,KeyError)):
                m.call(held,'profile_relation',data['view'],data['manifest'],data['code'],dependency,
                    observed=STATE['profile_raw'],producer_identity=data['quiet']['kernel_identity'])

        startup_relation_fixture(self)

    def test_13_same_process_or_later_reference_cannot_approve_current_profile(self):
        data=ensure()['producer'];m=data['module'];identity=ensure()['import']['quiet']['kernel_identity']
        with self.assertRaises(ValueError):
            m.call(m.get_program(data['held'],'validation'),'profile_relation',data['view'],data['manifest'],
                data['code'],STATE['profile_dependency'],observed=STATE['profile_raw'],producer_identity=identity)

    def test_14_dict_or_retired_actor_cannot_enter_retained_replay(self):
        data=ensure()['import']
        for actor in ({'quiet':data['quiet']},data['quiet_actor']):
            with self.assertRaises(ValueError):
                validation.replay_retained(data['view'],actor,data['manifest'],data['code'],data['argv'],data['stdout'],data['stderr'])

    def test_15_source_factory_rejects_unbound_bytes_and_false_child(self):
        raw=PARENT_PATH.read_bytes()
        with self.assertRaises(ValueError):parent.source_dispatch(raw,PIN(raw+b'x'))
        spec=parent.source_dispatch(raw,PIN(raw))
        with self.assertRaises(ValueError):FunctionType(spec[0],spec[1])(spec[2],'capture',(object(),b'{}',b'x',['x']))
        self.assertFalse((parent.OUT).exists())


def fault_actor(kind=None):
    data=ensure()['import'];m=private_parent('_ordinary_parent_fault_'+str(kind))
    original=m.dependencies
    held=original()
    qmodule=load(QUIET_PATH,'_ordinary_quiet_fault_'+str(kind))
    q=object.__new__(qmodule.ParentQuietActor)
    for name in qmodule.ParentQuietActor.__slots__:object.__setattr__(q,name,None)
    for name,value in dict(_creator=qmodule.creator(),_phase='CAPTURED',_result=CANONICAL(data['quiet']),
            _retired_evidence=None,_failure=None,_raws=(data['stdout'],data['stderr']),_pipes=()).items():
        object.__setattr__(q,name,value)
    qmodule._ACTORS[id(q)]=q
    original_retire=qmodule.retire
    def release(actor):return None
    def drain(actor,seconds):return 0,data['stdout'],data['stderr'],None,copy.deepcopy(data['quiet']['drain_observation'])
    def close(actor):return True
    def finish(actor):
        object.__setattr__(actor,'_phase','CLOSED')
        return json.loads(actor._result)
    def abort(actor,primary):return []
    qmodule.release=release;qmodule.drain_child=drain;qmodule.close_handle=close;qmodule.finish=finish;qmodule.abort=abort
    box={'retire_calls':0,'actor':None}
    if kind in ('retire_before','retire_after','parent_registry'):
        def retire(actor,evidence):
            box['retire_calls']+=1
            if kind=='retire_before' and box['retire_calls']==1:raise OSError('retire before mutation')
            result=original_retire(actor,evidence)
            if kind=='retire_after' and box['retire_calls']==1:raise OSError('retire after exact deletion')
            if kind=='parent_registry':
                m._PARENTS[id(box['actor'])]=box
            return result
        qmodule.retire=retire
    held=tuple((key,m.program(vars(qmodule)) if key=='quiet' else value) for key,value in held)
    if kind in ('row_cap','original_primary'):
        vmodule=load(VALID_PATH,'_ordinary_validation_fault_'+str(kind))
        if kind=='row_cap':
            def replay_retained(*args,**kwargs):return dict(accepted=True,noise='x'*1048576)
        else:
            primary=LookupError('original validation primary');primary.__cause__=BaseExceptionGroup('original cause',[OSError('source cleanup')])
            box['primary']=primary
            def replay_retained(*args,**kwargs):raise primary
        vmodule.replay_retained=replay_retained
        held=tuple((key,m.program(vars(vmodule)) if key=='validation' else value) for key,value in held)
    if kind in ('row_json','candidate_json','original_primary'):
        target='staged_saved_F_complete_parent_terminal_v1' if kind=='candidate_json' else 'staged_saved_F_complete_parent_receipt_v1'
        def canonical(value):
            if type(value) is dict and value.get('schema')==target:raise ArithmeticError('injected late JSON failure')
            return CANONICAL(value)
        m.canonical=canonical
    actor=object.__new__(m.ParentActor)
    for name in m.ParentActor.__slots__:object.__setattr__(actor,name,None)
    context=private_context(data['manifest'],data['code'],data['argv'])
    for name,value in dict(_creator=m.creator(),_program=m.program(vars(m)),_held=held,_process=None,_quiet=q,
        _plan=data['manifest'],_code=data['code'],_argv=CANONICAL(data['argv']),_context=CANONICAL(context),_profile=None,
        _phase='CAPTURED',_failure=None,_secondary=(),_raws=None,_quiet_snapshot=None,
        _result=CANONICAL(dict(schema='staged_saved_F_parent_publication_pending_v1',authority='DRAFT_NONAUTHORITATIVE',accepted=False)),
        _retirement_raw=None).items():object.__setattr__(actor,name,value)
    m._PARENTS[id(actor)]=actor;box['actor']=actor
    return m,actor,qmodule,q,box

class ParentFaultTests(unittest.TestCase):
    def test_16_held_sets_and_source_constant_images_are_immutable_or_guarded(self):
        data=ensure()['import'];m=data['module'];held=data['held']
        self.assertIs(type(held),tuple)
        with self.assertRaises(TypeError):held[0]=None
        v=m.get_program(held,'validation');namespace=v[2][0]
        original=namespace['_EXACT_CONTRACTS']
        try:
            namespace['_EXACT_CONTRACTS']=(('discovery',()),('import_discovery',{}),('producer',{}))
            with self.assertRaisesRegex(ValueError,'namespace binding'):m.call(v,'current')
        finally:namespace['_EXACT_CONTRACTS']=original
        keys=namespace['PROBE_KEYS']
        try:
            keys.add('caller_extension')
            with self.assertRaisesRegex(ValueError,'constant image'):m.call(v,'current')
        finally:keys.remove('caller_extension')
        self.assertIs(m.call(v,'current')[1]['actual_F'],False)
        copied_json=dict(v[0])['json'];original_copy=copied_json.loads
        try:
            copied_json.loads=lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('private copy replacement'))
            with self.assertRaisesRegex(ValueError,'private module namespace'):m.call(v,'current')
        finally:copied_json.loads=original_copy
        original_read=Path.read_bytes
        try:
            Path.read_bytes=lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('Path method replacement'))
            with self.assertRaisesRegex(ValueError,'class binding'):m.call(v,'current')
        finally:Path.read_bytes=original_read

        m2,actor,qmodule,q,box=fault_actor('row_json')
        original=m2.json.loads;executed=[]
        def replacement(*args,**kwargs):executed.append(True);raise AssertionError('replacement must not execute')
        try:
            m2.json.loads=replacement
            result=m2.dispatch(actor,'run',(1.,))
        finally:m2.json.loads=original
        self.assertEqual(executed,[]);self.assertIs(result['accepted'],False)
        self.assertIsNotNone(actor._result)
        if id(actor) in m2._PARENTS:m2._PARENTS.pop(id(actor))
        qmodule._ACTORS.pop(id(q),None)
        m3,actor3,qmodule3,q3,box3=fault_actor('row_json')
        private_json=dict(actor3._program[0])['json'];old_private=private_json.loads;executed=[]
        def private_replacement(*args,**kwargs):executed.append(True);raise AssertionError('private replacement executed')
        try:
            private_json.loads=private_replacement
            rejected=m3.dispatch(actor3,'run',(1.,))
        finally:private_json.loads=old_private
        self.assertEqual(executed,[]);self.assertIs(rejected['accepted'],False)
        self.assertIsNotNone(actor3._result)
        m3._PARENTS.pop(id(actor3),None);qmodule3._ACTORS.pop(id(q3),None)

    def test_17_capture_failure_preserves_primary_observation_and_retires_own_registry(self):
        data=ensure()['import'];m=private_parent('_ordinary_capture_failure')
        primary=LookupError('capture before quiet actor')
        def dependencies():raise primary
        def fallback(process):process.returncode=1;process._handle.closed=True;return []
        m.dependencies=dependencies;m.fallback=fallback
        process=object.__new__(subprocess.Popen);process.args=data['argv'];process.returncode=None;process.pid=9
        process._handle=SimpleNamespace(closed=False);process._child_created=False
        with self.assertRaises(RuntimeError) as caught:m.capture(process,data['manifest'],data['code'],data['argv'])
        actor=caught.exception.owner;self.assertIs(caught.exception.primary,primary)
        value=m.dispatch(actor,'observation',());self.assertIs(value['accepted'],False)
        self.assertEqual(value['failure']['primary']['message'],'capture before quiet actor')
        self.assertEqual(actor._phase,'RETIRED');self.assertNotIn(id(actor),m._PARENTS)
        self.assertIsNone(actor._process)
        self.assertEqual(validation.reopen_failure_terminal(CANONICAL(value))['terminal_parent_phase'],'RETIRED')

    def test_18_original_primary_and_recursive_cause_survive_late_row_json_failure(self):
        m,actor,qmodule,q,box=fault_actor('original_primary')
        value=m.dispatch(actor,'run',(1.,));core=value['failure']
        self.assertEqual(core['primary']['type'],'LookupError');self.assertEqual(core['primary']['cause']['type'],'ExceptionGroup')
        self.assertEqual(core['primary']['cause']['group'][0]['type'],'OSError')
        self.assertIn('ArithmeticError',[image['type'] for image in core['secondary']])
        self.assertNotIn(id(actor),m._PARENTS);self.assertNotIn(id(q),qmodule._ACTORS)
        metadata=LookupError('metadata leaf');metadata.secondary=['plain cleanup note'];metadata.cleanup=object()
        image=parent.error_image(metadata);self.assertEqual(image['secondary'][0]['error']['type'],'str')
        self.assertIs(validation.reopen_failure_terminal(CANONICAL(value))['accepted'],False)

    def test_19_row_candidate_json_and_row_cap_faults_have_closed_failed_replay(self):
        for kind in ('row_json','candidate_json','row_cap'):
            m,actor,qmodule,q,box=fault_actor(kind)
            value=m.dispatch(actor,'run',(1.,))
            with self.subTest(kind=kind):
                self.assertIs(value['accepted'],False);self.assertEqual(value['schema'],'staged_saved_F_complete_parent_failure_v1')
                self.assertEqual(value['terminal_parent_phase'],'RETIRED')
                self.assertNotIn(id(actor),m._PARENTS);self.assertNotIn(id(q),qmodule._ACTORS)
                self.assertIs(validation.reopen_failure_terminal(CANONICAL(value))['accepted'],False)
                self.assertEqual(base64.b64decode(value['failure']['stdout_raw_base64']),ensure()['import']['stdout'])

    def test_20_retire_faults_before_and_after_exact_deletion_preserve_failure_and_close_registry(self):
        for kind in ('retire_before','retire_after'):
            m,actor,qmodule,q,box=fault_actor(kind)
            value=m.dispatch(actor,'run',(1.,))
            with self.subTest(kind=kind):
                self.assertIs(value['accepted'],False);self.assertEqual(value['failure']['primary']['type'],'OSError')
                self.assertEqual(value['terminal_parent_phase'],'RETIRED')
                self.assertNotIn(id(actor),m._PARENTS);self.assertNotIn(id(q),qmodule._ACTORS)
                self.assertIs(validation.reopen_failure_terminal(CANONICAL(value))['accepted'],False)
                if kind=='retire_after':self.assertIsNotNone(value['failure']['prior_retirement_parent_result_pin'])

    def test_21_foreign_parent_registry_row_is_preserved_and_terminal_stays_unresolved(self):
        m,actor,qmodule,q,box=fault_actor('parent_registry')
        try:
            value=m.dispatch(actor,'run',(1.,))
            self.assertIs(value['accepted'],False);self.assertEqual(value['terminal_parent_phase'],'UNRESOLVED')
            self.assertIs(m._PARENTS[id(actor)],box);self.assertIsNotNone(actor._result)
            self.assertNotIn(id(q),qmodule._ACTORS)
            self.assertEqual(validation.reopen_failure_terminal(CANONICAL(value))['terminal_parent_phase'],'UNRESOLVED')
        finally:m._PARENTS.pop(id(actor),None)

    def test_22_rejected_terminal_field_and_stream_pin_tampering_rejects(self):
        m,actor,qmodule,q,box=fault_actor('row_json');value=m.dispatch(actor,'run',(1.,))
        for field in ('accepted','failure_pin','stdout_pin','extra'):
            changed=copy.deepcopy(value)
            if field=='accepted':changed['accepted']=True
            elif field=='failure_pin':changed['failure_pin']['sha256']='0'*64
            elif field=='stdout_pin':changed['failure']['stdout_pin']['sha256']='0'*64;changed['failure_pin']=PIN(CANONICAL(changed['failure']))
            else:changed['extra']=False
            with self.subTest(field=field),self.assertRaises((ValueError,AssertionError,KeyError)):
                validation.reopen_failure_terminal(CANONICAL(changed))
        m2,actor2,qmodule2,q2,box2=fault_actor('row_json')
        def broken_failure(*args,**kwargs):raise OSError('failure handler itself failed')
        m2.failure_terminal=broken_failure
        # Rebind only the private fixture before entry, to exercise the emergency source code.
        object.__setattr__(actor2,'_program',m2.program(vars(m2)))
        emergency=m2.dispatch(actor2,'run',(1.,))
        self.assertEqual(emergency['schema'],'staged_saved_F_parent_emergency_failure_v1')
        self.assertEqual(emergency['primary']['type'],'ArithmeticError')
        self.assertEqual(emergency['terminal_parent_phase'],'UNRESOLVED')
        self.assertIs(validation.reopen_failure_terminal(CANONICAL(emergency))['accepted'],False)
        m2._PARENTS.pop(id(actor2),None);qmodule2._ACTORS.pop(id(q2),None)

    def test_23_source_function_code_drift_rejects_before_dependency_call(self):
        data=ensure()['import'];m=data['module'];held=m.get_program(data['held'],'validation')
        namespace=held[2][0];function=namespace['canonical'];code=function.__code__
        def replacement(value):raise AssertionError('caller replacement must not execute')
        try:
            function.__code__=replacement.__code__
            with self.assertRaisesRegex(ValueError,'function metadata'):m.call(held,'current')
        finally:function.__code__=code

if __name__=='__main__':unittest.main()
