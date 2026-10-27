"""Bounded development parent; serialized child facts are never role authority."""
import ast
import base64
import ctypes as C
from ctypes import wintypes as W
from hashlib import sha256
import importlib.util
import json
import math
import io
import tokenize
import os
from pathlib import Path
import secrets
import subprocess
from threading import Thread
import time
import zlib

ROOT=Path('D:/CUHKSZ/Research Project/electricity-grid')
OUT=ROOT/'results/tables/staged_rts24_saved_fresh_rti_v2_non_authoritative'
RUNTIME=Path('D:/Miniconda3/envs/compute'); EXE=RUNTIME/'python.exe'
CORE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v13.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v10.py'
SOURCE_CONTROL=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/admission_repair.json'
DRAIN=ROOT/'results/tables/staged_rts24_saved_fresh_wire_data_v1_non_authoritative/checks_01/run.py'
SOURCE_SHA='acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'
FALSE_FIELDS=('external_expected_truth_verified','upstream_owner_verified','parent_independently_authenticated_python_object_graph',
    'startup_tcb_authenticated','independent_root_verified','native_behavior_verified','full_runtime_binding_verified',
    'full_P1_content_verified','role_bootstrap','permit_issued','native_authorized','F_launch_admitted','actual_F',
    'run_authority','scientific_evidence_adopted','resource_admission','formal_result','production_seal')


def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def save(path,value):
    with path.open('xb') as stream:stream.write(canonical(value))
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def transport():
    original=CORE.read_bytes()+b'\n'+PROBE.read_bytes()
    marker=b'\nimport builtins\n';assert original.count(marker)==1
    prefix,tail=original.split(marker,1);payload=b'import builtins\n'+tail
    assert prefix+b'\n'+payload==original
    source_payload=payload
    lines=payload.decode('utf-8').splitlines(keepends=True)
    for token in tokenize.tokenize(io.BytesIO(payload).readline):
        if token.type==tokenize.COMMENT:
            line,col=token.start;end=token.end[1];lines[line-1]=lines[line-1][:col]+(' '*(end-col))+lines[line-1][end:]
    payload=''.join(lines).encode('utf-8')
    assert ast.dump(ast.parse(payload),include_attributes=True)==ast.dump(ast.parse(source_payload),include_attributes=True)
    assert compile(payload,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0)==compile(source_payload,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0)
    compressor=zlib.compressobj(9,zlib.DEFLATED,zlib.MAX_WBITS,8,zlib.Z_DEFAULT_STRATEGY,zdict=prefix)
    packed=base64.b85encode(compressor.compress(payload)+compressor.flush())
    beginning=(b'\nimport os as _bootstrap_os\n'
        +b'if _bootstrap_os.__spec__.origin!="frozen": raise RuntimeError("frozen OS startup root required")\n'
        +b'_DLL_DIRECTORY=_bootstrap_os.add_dll_directory("D:/Miniconda3/envs/compute/Library/bin")\n')
    beginning+=b'_DLL_DIRECTORY_CLOSE_STATE=[False]\n'
    body=(b'import zlib as _transport_zlib\nimport base64 as _transport_base64\n'
        +b"_unpacker=_transport_zlib.decompressobj(zdict=sys.orig_argv[6].partition('\\nimport os as _bootstrap_os\\n')[0].encode('utf-8'))\n"
        +b'_PAYLOAD_RAW=_unpacker.decompress(_transport_base64.b85decode('+repr(packed).encode()+b'),131073)\n'
        +b'if len(_PAYLOAD_RAW)>131072 or not _unpacker.eof or _unpacker.unconsumed_tail or _unpacker.unused_data: raise RuntimeError("bootstrap payload cap")\n'
        +b'_PAYLOAD_CODE=compile(_PAYLOAD_RAW,"<pre_entry_payload>","exec",dont_inherit=True,optimize=0)\n'
        +b'exec(_PAYLOAD_CODE,globals())\n')
    loader=beginning+b'try:\n'+b''.join(b' '+line+b'\n' for line in body.splitlines())+b'finally:\n if not _DLL_DIRECTORY_CLOSE_STATE[0]:\n  _DLL_DIRECTORY_CLOSE_STATE[0]=True\n  _DLL_DIRECTORY.close()\n'
    assert ast.dump(ast.parse(prefix+b'\n'+payload))==ast.dump(ast.parse(original))
    return prefix+loader


def environment():
    result={n:os.environ[n] for n in ('SYSTEMROOT','WINDIR','TEMP','TMP','USERPROFILE') if n in os.environ}
    system=Path(result['SYSTEMROOT'])
    result['PATH']=';'.join(str(p) for p in (RUNTIME,RUNTIME/'DLLs',RUNTIME/'Library/bin',system/'System32',system))
    result.update(PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    return result


def source():
    raw=SOURCE_CONTROL.read_bytes()
    assert pin(raw)==dict(bytes=21981,sha256='f147def983e56f538dc3252d270ad335b83f5a381853c8a42deb281d2ead7244')
    sources=json.loads(raw)['source_pins'];assert pin(canonical(sources))['sha256']==SOURCE_SHA
    for name,expected in sources.items():assert pin((ROOT/name).read_bytes())==expected
    return sources


def manifest(case,code):
    selected={str(RUNTIME/n):pin((RUNTIME/n).read_bytes()) for n in ('python312.dll','DLLs/_ctypes.pyd','Lib/ctypes/__init__.py','Lib/ctypes/wintypes.py','Lib/subprocess.py','Lib/encodings/__init__.py')}
    absent=[str(RUNTIME/n) for n in ('python312._pth','python._pth','pyvenv.cfg','python312.zip')]+[str(RUNTIME.parent/'pyvenv.cfg')]
    assert all(not os.path.lexists(n) for n in absent)
    profile=None
    if case not in ('discovery',):
        admission=json.loads((OUT/'profile_admission.json').read_bytes())
        assert admission['profile_pin']==pin((OUT/'startup_profile.json').read_bytes()) and admission['transport_pin']==pin(code)
        assert admission['environment_pin']==pin(canonical(environment())) and admission['accepted'] is True
        assert admission['registration_pin']==pin((OUT/'registration.json').read_bytes())
        assert admission['discovery_receipt_pin']==pin((OUT/'probe_discovery.receipt.json').read_bytes())
        for path,expected in admission['helper_pins'].items():assert pin(Path(path).read_bytes())==expected
        profile=dict(path=str(OUT/'startup_profile.json'),pin=admission['profile_pin'])
    import_profile=None
    if case not in ('discovery','import_discovery'):
        admitted=json.loads((OUT/'import_admission.json').read_bytes());assert admitted['accepted'] is True and admitted['transport_pin']==pin(code)
        assert admitted['profile_pin']==pin((OUT/'import_profile.json').read_bytes())
        import_profile=dict(path=str(OUT/'import_profile.json'),pin=admitted['profile_pin'])
    return dict(schema='staged_saved_F_runtime_handoff_manifest_v1',authority='DRAFT_NONAUTHORITATIVE',nonce=secrets.token_hex(16),
        source_pins=source(),source_epoch=SOURCE_SHA,bootstrap_pin=pin(code),executable_pin=pin(EXE.read_bytes()),
        python='3.12.12 | packaged by Anaconda, Inc. | (main, Oct 21 2025, 20:05:38) [MSC v.1929 64 bit (AMD64)]',
        environment=environment(),cwd=str(ROOT),initial_paths=[str(RUNTIME/'python312.zip'),str(RUNTIME/'DLLs'),str(RUNTIME/'Lib'),str(RUNTIME)],
        selected_runtime_file_observations=selected,startup_absent=absent,startup_profile=profile,namespace_helper=dict(path=str(ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_timing_v1.py'),pin=pin((ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_timing_v1.py').read_bytes())),import_helper=dict(path=str(ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_timing_v1.py'),pin=pin((ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_timing_v1.py').read_bytes())),import_policy=dict(path=str(OUT/'import_policy.json'),pin=pin((OUT/'import_policy.json').read_bytes())),import_profile=import_profile,case=case)


def process_api():
    api=C.WinDLL('kernel32',use_last_error=True)
    for name,args,result in [('GetProcessId',[W.HANDLE],W.DWORD),('GetProcessTimes',[W.HANDLE]+[C.POINTER(W.FILETIME)]*4,W.BOOL),
        ('QueryFullProcessImageNameW',[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)],W.BOOL),('GetHandleInformation',[W.HANDLE,C.POINTER(W.DWORD)],W.BOOL)]:
        fn=getattr(api,name);fn.argtypes=args;fn.restype=result
    return api


def kernel_identity(api,process):
    created,ended,kernel,user=(W.FILETIME() for _ in range(4))
    assert api.GetProcessId(process._handle)==process.pid and api.GetProcessTimes(process._handle,*[C.byref(x) for x in (created,ended,kernel,user)])
    image=C.create_unicode_buffer(32768);size=W.DWORD(len(image))
    assert api.QueryFullProcessImageNameW(process._handle,0,image,C.byref(size)) and Path(image.value)==EXE
    return dict(pid=process.pid,creation=created.dwLowDateTime|created.dwHighDateTime<<32,image_path=image.value)


def base_compare_child(case,code,stdout,stderr,child_code,identity,argv,writer_errors):
    assert not stderr and not writer_errors
    record=json.loads(stdout);assert canonical(record)+b'\n'==stdout
    if record.get('import_profile') is not None:
        encoded=record['import_profile'];assert set(encoded)=={'encoding','raw_pin','data'} and encoded['encoding']=='zlib_base64'
        unpacker=zlib.decompressobj();raw=unpacker.decompress(base64.b64decode(encoded['data'],validate=True),1024**2+1)
        assert len(raw)<=1024**2 and unpacker.eof and not unpacker.unconsumed_tail and not unpacker.unused_data and pin(raw)==encoded['raw_pin']
        profile=json.loads(raw);assert canonical(profile)==raw;record['import_profile']=profile
    assert record['schema']=='staged_saved_F_runtime_handoff_probe_v1' and record['authority']=='DRAFT_NONAUTHORITATIVE'
    assert record['case']==case and record['source_epoch']==SOURCE_SHA and all(record[k] is False for k in FALSE_FIELDS)
    assert record['dll_directory_close_returned'] is True and record['live_at_report'] is False
    if case=='discovery':
        assert child_code==0 and record['status']=='discovery_only' and record['startup_profile'] is not None
        assert record['self_handles_closed'] is None and record['primary'] is None and record['secondary']==[]
        profile=record['startup_profile'];assert profile['bootstrap_pin']==pin(code) and profile['environment_sha']==pin(canonical(environment()))
        for name,expected in profile['disk_file_observations'].items():
            assert Path(name).is_relative_to(RUNTIME) and pin(Path(name).read_bytes())==expected
        save(OUT/'startup_profile.json',profile)
        return dict(startup_profile_pin=pin(canonical(profile)),discovery_only=True,child_record=record)
    assert record['self_handles_closed'] is True and record['close_calls']==[1,1]
    assert record['source_phase']=='CONSUMED' and record['namespace_alias_absent'] is True
    guard=record['guard'];assert guard['sentinel']==1 and guard['faults']==[] and record['early_audit_blocked']==[]
    assert guard['protected_open_attempts']==guard['write_attempts']==guard['process_attempts']==0
    assert guard['events'].index('self_handles_live')<guard['events'].index('source_read_begin')<guard['events'].index('transfer_committed')
    if case in ('normal','import_discovery'):
        assert child_code==0 and record['status']=='completed' and record['primary'] is None and record['secondary']==[]
        assert record['runtime_phase']=='CLOSED' and record['inputs_phase']==record['namespace_phase']=='CONSUMED'
        assert record['runtime_is_resource_owner'] and record['old_inputs_successor_matches'] and record['old_namespace_successor_matches']
        assert record['runtime_was_live'] is (case=='normal') and record['boundary_phase']=='CLOSED'
        assert record['retained_modules']>0 and record['source_bookends']>0 and record['import_profile'] is not None
        br=record['boundary_report'];assert br['installation_sentinel_observed']==br['audit_handoff_observed']==1
        assert br['optional_Popen_attempts']==1 and br['machinery_authenticated_stage']==br['machinery_observed_stage']==2
        assert br['import_boundary_completed'] and br['violations']==0
        if case=='import_discovery':save(OUT/'import_profile.json',record['import_profile'])
    else:
        assert child_code==1 and record['status']=='failed' and record['primary'] is not None
        if case=='precommit':
            assert record['runtime_phase'] is None and record['inputs_phase']=='CLOSED' and record['namespace_phase']=='UNRESOLVED'
            assert record['primary']['message']=='injected_runtime_precommit'
        else:
            assert record['runtime_phase']=='UNRESOLVED' and record['runtime_is_resource_owner']
            assert record['old_inputs_successor_matches'] and record['old_namespace_successor_matches']
            assert record['inputs_phase']==record['namespace_phase']=='CONSUMED'
            assert record['failure_phase']==('TRANSFER' if case=='postcommit' else 'IMPORT_SETUP' if case in ('blocked_installation','handoff_middle') else 'IMPORT')
            if case=='postcommit':assert record['primary']['primary']['message']=='injected_runtime_postcommit'
            if case=='blocked_installation':assert record['boundary_report']['installation_sentinel_observed']==0
            if case=='handoff_middle':assert record['boundary_report']['audit_handoff_observed']==0
            if case=='M_only':assert record['boundary_report']['machinery_observed_stage']==1
            if case=='after_D':assert record['boundary_report']['machinery_observed_stage']==2
    kernel=record['kernel_identity'];assert (kernel['pid'],kernel['process_creation_filetime'])==(identity['pid'],identity['creation'])
    assert Path(kernel['image_path'])==EXE and kernel['command_line_sha']==pin(subprocess.list2cmdline(argv).encode('utf-8'))
    return dict(child_record=record,parent_kernel_identity_matched=True,parent_python_graph_attested=False)


def parse_diagnostic_stderr(raw):
    stages=[];graphs=[];other=[];malformed=[]
    allowed={'loader_ready','before_adapter_import','after_adapter_import_attempt','adapter_import_returned','machinery_authenticated','before_adapter_roots','after_adapter_roots','before_boundary_close','after_boundary_close'}
    for line in raw.splitlines(keepends=True):
        if not line.endswith(b'\n'):other.append(line);continue
        try:row=json.loads(line)
        except (ValueError,UnicodeDecodeError):other.append(line);continue
        if type(row) is list and len(row)==3 and row[0]=='stage' and type(row[1]) is str and row[1] in allowed and type(row[2]) is float and math.isfinite(row[2]):stages.append(row)
        elif type(row) is list and len(row)==2 and row[0] in ('enter','exit') and type(row[1]) is float and math.isfinite(row[1]):graphs.append(row)
        else:malformed.append(line);other.append(line)
    residual=b''.join(other)
    return dict(stages=stages,graph_frames=graphs,non_stage_raw_base64=base64.b64encode(residual).decode(),non_stage_pin=pin(residual),unclassified_json_lines=len(malformed),
        stack_present=b'Timeout (0:00:02)!' in residual and b'Thread ' in residual,stage_parse_complete=False)

def validate_diagnostic_record(case,stdout,child_code,identity,argv):
    record=json.loads(stdout);assert canonical(record)+b'\n'==stdout
    assert record['schema']=='staged_saved_F_runtime_handoff_probe_v1' and record['authority']=='DRAFT_NONAUTHORITATIVE'
    assert record['case']==case=='import_discovery' and record['source_epoch']==SOURCE_SHA
    assert all(record[name] is False for name in FALSE_FIELDS) and record['live_at_report'] is False
    assert record['status'] in ('completed','failed') and child_code==(0 if record['status']=='completed' else 1)
    assert type(record['secondary']) is list and type(record['self_handles_closed']) is bool
    calls=record['close_calls'];assert type(calls) is list and len(calls)==2 and all(type(value) is int and value in (0,1) for value in calls)
    assert record['source_phase']==record['inputs_phase']==record['namespace_phase']=='CONSUMED'
    assert record['runtime_is_resource_owner'] is True and record['old_inputs_successor_matches'] is True and record['old_namespace_successor_matches'] is True
    assert record['resource_phase'] in ('CLOSED','UNRESOLVED') and record['runtime_phase'] in ('CLOSED','UNRESOLVED')
    assert type(record['dll_directory_close_returned']) is bool and type(record['namespace_alias_absent']) is bool
    if record['self_handles_closed']:assert calls==[1,1] and record['resource_phase']=='CLOSED'
    else:assert record['resource_phase']=='UNRESOLVED'
    if record['status']=='completed':
        assert record['primary'] is None and record['secondary']==[] and record['runtime_phase']=='CLOSED' and record['boundary_phase']=='CLOSED'
        assert record['self_handles_closed'] and record['dll_directory_close_returned'] and record['namespace_alias_absent']
        assert record['import_profile'] is not None and record['runtime_was_live'] is False
        encoded=record['import_profile'];assert set(encoded)=={'encoding','raw_pin','data'} and encoded['encoding']=='zlib_base64'
        unpacker=zlib.decompressobj();raw=unpacker.decompress(base64.b64decode(encoded['data'],validate=True),1024**2+1)
        assert len(raw)<=1024**2 and unpacker.eof and not unpacker.unconsumed_tail and not unpacker.unused_data and pin(raw)==encoded['raw_pin']
        assert canonical(json.loads(raw))==raw
    else:assert record['primary'] is not None or record['secondary']
    kernel=record['kernel_identity'];assert (kernel['pid'],kernel['process_creation_filetime'])==(identity['pid'],identity['creation'])
    assert Path(kernel['image_path'])==EXE and kernel['command_line_sha']==pin(subprocess.list2cmdline(argv).encode('utf-8'))
    witness=record['self_handles_closed'] and calls==[1,1] and record['resource_phase']=='CLOSED' and record['dll_directory_close_returned'] and record['namespace_alias_absent']
    return record,witness

def compare_child(case,code,stdout,stderr,child_code,identity,argv,writer_errors):
    if case=='discovery':return base_compare_child(case,code,stdout,stderr,child_code,identity,argv,writer_errors)
    parsed=parse_diagnostic_stderr(stderr);assert parsed['stages'] and any(row[1]=='before_adapter_import' for row in parsed['stages']) and not writer_errors
    record,witness=(None,False) if not stdout else validate_diagnostic_record(case,stdout,child_code,identity,argv)
    return dict(child_record=record,diagnostic=parsed,self_close_witness_present=witness,adapter_import_attempts_upper_bound=1,adapter_import_return_observed=any(v[1]=='adapter_import_returned' for v in parsed['stages']),diagnostic_only=True)

def one_case(case,seconds):
    started=time.perf_counter(); code=transport(); plan=manifest(case,code); expected=canonical(plan); plan_path=OUT/('probe_'+case+'.plan.json')
    if case=='path':plan['initial_paths']=[str(ROOT),*plan['initial_paths'][1:]];expected=canonical(plan)
    actual=expected if case!='manifest_flip' else expected[:-1]+b'!'
    with plan_path.open('xb') as stream:stream.write(actual)
    argv=[str(EXE),'-P','-B','-s','-S','-c',code.decode('utf-8'),'--pre-entry-lease',str(plan_path),pin(expected)['sha256']]
    if case=='flags':argv.remove('-P')
    assert len(subprocess.list2cmdline(argv).encode('utf-16-le'))//2<=30000
    env=dict(plan['environment'])
    if case=='environment':env['OMP_NUM_THREADS']='2'
    assert pin(DRAIN.read_bytes())==dict(bytes=12125,sha256='b504c6d5bcd31412e8f7c03f6bd84094e3895e818c830853501f58fce6c13e59')
    drain=load(DRAIN,'pre_entry_fixed_drain');drain.STDOUT_CAP=131072;drain.STDERR_CAP=32768
    api=process_api(); process=None; writer=None; writer_errors=[]; released=[False]; stdin_closed=[False]
    stdout=stderr=b''; child_code=None; identity=None; observation=None; closed=False; primary=None; cleanup=[]; result=None
    try:
        process=subprocess.Popen(argv,executable=str(EXE),cwd=ROOT,env=env,creationflags=subprocess.CREATE_NO_WINDOW,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        identity=kernel_identity(api,process)
        def release():
            try:
                process.stdin.write(b'SAVED_PRE_ENTRY_V1:'+pin(expected)['sha256'].encode('ascii')+b'\n');process.stdin.flush();released[0]=True
            except BaseException as error:writer_errors.append(type(error).__name__)
            finally:
                try:process.stdin.close();stdin_closed[0]=True
                except BaseException as error:writer_errors.append(type(error).__name__)
        if case!='timeout':writer=Thread(target=release,daemon=True);writer.start()
        child_code,stdout,stderr,error,observation=drain.drain(process,seconds-(time.perf_counter()-started)-0.5)
        if writer is not None:writer.join(.5)
        else:process.stdin.close();stdin_closed[0]=True
        assert writer is None or not writer.is_alive()
        assert observation['pipes_closed'] and observation['reader_threads_terminal'] and not observation['cleanup'] and not observation['reader_errors']
        assert not observation['stdout_truncated'] and not observation['stderr_truncated']
        if case=='import_discovery':assert error is None or error=='timeout'
        elif case=='timeout':assert error=='timeout' and observation['killed'] and not released[0]
        else:assert error is None and not observation['killed']
        if case!='flags':assert not writer_errors
        result=compare_child(case,code,stdout,stderr,child_code,identity,argv,writer_errors)
        assert plan_path.read_bytes()==actual and source()==plan['source_pins']
        assert all(not os.path.lexists(n) for n in plan['startup_absent'])
    except BaseException as error:primary=type(error).__name__+':'+str(error)[:160]
    finally:
        if process is not None:
            if process.poll() is None:
                try:process.kill();process.wait(timeout=1)
                except BaseException as error:cleanup.append('kill_wait:'+type(error).__name__)
            child_code=process.returncode
            if writer is not None:writer.join(.5)
            if writer is None or not writer.is_alive():
                try:process.stdin.close();stdin_closed[0]=True
                except BaseException as error:cleanup.append('stdin:'+type(error).__name__)
            else:cleanup.append('writer_thread_pending')
            try:
                handle=int(process._handle);process._handle.Close();flags=W.DWORD();C.set_last_error(0)
                closed=process._handle.closed and not api.GetHandleInformation(W.HANDLE(handle),C.byref(flags)) and C.get_last_error()==6
            except BaseException as error:cleanup.append('process_handle:'+type(error).__name__)
    record=dict(authority='DRAFT_NONAUTHORITATIVE',case=case,accepted=primary is None and not cleanup and closed and stdin_closed[0],
        charged_seconds=time.perf_counter()-started,cap_seconds=seconds,primary=primary,cleanup=cleanup,result=result,
        plan_pin=pin(actual),expected_manifest_pin=pin(expected),transport_pin=pin(code),child_exit=child_code,parent_kernel_identity=identity,
        release_sent=released[0],writer_errors=writer_errors,writer_thread_terminal=writer is None or not writer.is_alive(),stdin_closed=stdin_closed[0],
        parent_process_handle_closed=closed,bounded_drain=observation,stdout_pin=pin(stdout),stderr_pin=pin(stderr),
        stdout_raw_base64=base64.b64encode(stdout).decode(),stderr_raw_base64=base64.b64encode(stderr).decode(),
        **{k:False for k in FALSE_FIELDS})
    record['accepted']=record['accepted'] and record['charged_seconds']<=seconds
    if case in ('discovery','import_discovery'): save(OUT/('probe_'+case+'.receipt.json'),record)
    else:
        journal=OUT/'probe_cases.receipts.jsonl'
        prior=[] if not journal.exists() else [json.loads(line) for line in journal.read_bytes().splitlines()]
        if journal.exists(): assert journal.read_bytes()==b''.join(canonical(row)+b'\n' for row in prior)
        order=('normal','precommit','postcommit','blocked_installation','handoff_middle','M_only','after_D')
        assert [row['case'] for row in prior]==list(order[:order.index(case)])
        with journal.open('ab' if prior else 'xb') as stream: stream.write(canonical(record)+b'\n')
    return record
