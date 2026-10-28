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
OUT=ROOT/'results/tables/staged_rts24_saved_fresh_project_construction_v2_non_authoritative'
RUNTIME=Path('D:/Miniconda3/envs/compute'); EXE=RUNTIME/'python.exe'
CORE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v41.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v39.py'
SOURCE_CONTROL=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/admission_repair.json'
DRAIN=ROOT/'experiments/staged_rts24_saved_fresh_memory_drain_v1.py'
SOURCE_SHA='acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'
FALSE_FIELDS=('external_expected_truth_verified','upstream_owner_verified','parent_independently_authenticated_python_object_graph',
    'startup_tcb_authenticated','independent_root_verified','native_behavior_verified','full_runtime_binding_verified',
    'full_P1_content_verified','role_bootstrap','permit_issued','native_authorized','F_launch_admitted','actual_F',
    'run_authority','scientific_evidence_adopted','resource_admission','formal_result','production_seal')


def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def save(path,value):
    raw=canonical(value);assert len(raw)<=1048576,'diagnostic artifact byte cap'
    with path.open('xb') as stream:stream.write(raw)
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def minify_prefix(prefix):
    before = prefix
    tokens = list(tokenize.tokenize(io.BytesIO(prefix).readline))
    lines = prefix.decode('utf-8').splitlines(keepends=True)
    edits = []
    skip = {tokenize.ENCODING, tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}
    words = {tokenize.NAME, tokenize.NUMBER, tokenize.STRING}
    for left, right in zip(tokens, tokens[1:]):
        if left.type in skip or right.type in skip or left.end[0] != right.start[0]:
            continue
        row, a = left.end
        b = right.start[1]
        gap = lines[row - 1][a:b]
        if not gap or not gap.isspace():
            continue
        separate = left.type in words and right.type in words or (left.type == tokenize.NUMBER and right.string == '.')
        separate = separate or (left.type == right.type == tokenize.OP and (left.string + right.string in tokenize.EXACT_TOKEN_TYPES or left.string.endswith('.') or right.string.startswith('.')))
        edits.append((row - 1, a, b, ' ' if separate else ''))
    for row, a, b, value in reversed(edits):
        lines[row] = lines[row][:a] + value + lines[row][b:]
    prefix = ''.join(lines).encode('utf-8')
    assert [(t.type, t.string) for t in tokenize.tokenize(io.BytesIO(prefix).readline)] == [(t.type, t.string) for t in tokens]
    assert ast.dump(ast.parse(prefix)) == ast.dump(ast.parse(before)) and prefix.count(b'\n') == before.count(b'\n')

    def code_image(code):
        names = ('co_argcount', 'co_posonlyargcount', 'co_kwonlyargcount', 'co_nlocals', 'co_stacksize', 'co_flags', 'co_code', 'co_names', 'co_varnames', 'co_freevars', 'co_cellvars', 'co_filename', 'co_name', 'co_qualname', 'co_firstlineno', 'co_exceptiontable')
        return (tuple((getattr(code, n) for n in names)), tuple((code_image(v) if type(v) is type(code) else v for v in code.co_consts)), tuple(code.co_lines()))
    tokens_after = list(tokenize.tokenize(io.BytesIO(prefix).readline))
    assert not any((t.type == tokenize.STRING and t.start[0] != t.end[0] for t in tokens_after))
    lines = prefix.decode('utf-8').splitlines(keepends=True)
    for index, line in enumerate(lines):
        text = line.lstrip(' ')
        if not text.strip() or text.startswith('#'):
            continue
        leading = len(line) - len(text)
        assert leading % 4 == 0 and (not text.startswith('\t'))
        lines[index] = ' ' * (leading // 4) + text
    prefix = ''.join(lines).encode('utf-8')
    after = list(tokenize.tokenize(io.BytesIO(prefix).readline))
    canonical = lambda ts: [(t.type, '' if t.type == tokenize.INDENT else t.string) for t in ts]
    assert canonical(after) == canonical(tokens)
    assert ast.dump(ast.parse(prefix)) == ast.dump(ast.parse(before)) and prefix.count(b'\n') == before.count(b'\n')
    assert code_image(compile(prefix, '<pre_entry_prefix>', 'exec', dont_inherit=True, optimize=0)) == code_image(compile(before, '<pre_entry_prefix>', 'exec', dont_inherit=True, optimize=0))
    return prefix

def transport():return TRANSPORT.build(CORE,PROBE,minify_prefix)


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
    assert case in ('discovery','import_discovery'),'construction diagnostic only; no producer admission'
    selected={str(RUNTIME/n):pin((RUNTIME/n).read_bytes()) for n in ('python312.dll','DLLs/_ctypes.pyd','Lib/ctypes/__init__.py','Lib/ctypes/wintypes.py','Lib/subprocess.py','Lib/encodings/__init__.py')}
    absent=[str(RUNTIME/n) for n in ('python312._pth','python._pth','pyvenv.cfg','python312.zip')]+[str(RUNTIME.parent/'pyvenv.cfg')]
    assert all(not os.path.lexists(n) for n in absent)
    profile=None
    if case not in ('discovery',):
        packed=json.loads((OUT/'profile_admission.exit.json').read_bytes());assert packed['accepted'] is True
        item=packed['embedded_artifacts']['admission'];assert item['encoding']=='canonical_json'
        raw=base64.b64decode(item['raw_base64'],validate=True);assert pin(raw)==item['pin']
        admission=json.loads(raw);assert canonical(admission)==raw
        assert admission['profile_pin']==pin((OUT/'startup_profile.json').read_bytes()) and admission['transport_pin']==pin(code)
        assert admission['environment_pin']==pin(canonical(environment())) and admission['accepted'] is True
        assert admission['registration_pin']==pin((OUT/'registration.json').read_bytes())
        assert admission['discovery_receipt_pin']==pin((OUT/'probe_discovery.receipt.json').read_bytes())
        for path,expected in admission['helper_pins'].items():assert pin(Path(path).read_bytes())==expected
        profile=dict(path=str(OUT/'startup_profile.json'),pin=admission['profile_pin'])
    import_profile=None
    if case=='normal':
        from types import SimpleNamespace
        admitted,_=REFERENCE.admission(SimpleNamespace(**globals()),code)
        import_profile=admitted['reference_source']['reference']
    elif case not in ('discovery','import_discovery'):
        admitted=json.loads((OUT/'import_admission.json').read_bytes());assert admitted['accepted'] is True and admitted['transport_pin']==pin(code)
        assert admitted['profile_pin']==pin((OUT/'import_profile.json').read_bytes())
        import_profile=dict(path=str(OUT/'import_profile.json'),pin=admitted['profile_pin'])
    plan=dict(schema='staged_saved_F_project_construction_manifest_v2',authority='DRAFT_NONAUTHORITATIVE',nonce=secrets.token_hex(16),
        source_pins=source(),source_epoch=SOURCE_SHA,bootstrap_pin=pin(code),executable_pin=pin(EXE.read_bytes()),
        python='3.12.12 | packaged by Anaconda, Inc. | (main, Oct 21 2025, 20:05:38) [MSC v.1929 64 bit (AMD64)]',
        environment=environment(),cwd=str(ROOT),initial_paths=[str(RUNTIME/'python312.zip'),str(RUNTIME/'DLLs'),str(RUNTIME/'Lib'),str(RUNTIME)],
        selected_runtime_file_observations=selected,startup_absent=absent,startup_profile=profile,namespace_helper=dict(path=str(ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v3.py'),pin=pin((ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v3.py').read_bytes())),import_helper=dict(path=str(ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v4.py'),pin=pin((ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v4.py').read_bytes())),import_policy=dict(path=str(OUT/'import_policy.json'),pin=pin((OUT/'import_policy.json').read_bytes())),import_profile=import_profile,producer_helpers=producer_references(),graph_contract=construction_graph_contract(),case=case)
    validate_manifest_pair(plan,code)
    return plan


def process_api():
    api=C.WinDLL('kernel32',use_last_error=True)
    for name,args,result in [('GetProcessId',[W.HANDLE],W.DWORD),('GetProcessTimes',[W.HANDLE]+[C.POINTER(W.FILETIME)]*4,W.BOOL),
        ('QueryFullProcessImageNameW',[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)],W.BOOL),('GetHandleInformation',[W.HANDLE,C.POINTER(W.DWORD)],W.BOOL)]:
        fn=getattr(api,name);fn.argtypes=args;fn.restype=result
    return api


def memory_observation(process):

    class Counters(C.Structure):
        _fields_ = [('cb', W.DWORD), ('PageFaultCount', W.DWORD)] + [(n, C.c_size_t) for n in ('PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
    try:
        mem = C.WinDLL('psapi', use_last_error=True).GetProcessMemoryInfo
        mem.argtypes = [W.HANDLE, C.POINTER(Counters), W.DWORD]
        mem.restype = W.BOOL
        counters = Counters()
        counters.cb = C.sizeof(counters)
        if not mem(W.HANDLE(int(process._handle)), C.byref(counters), counters.cb):
            return dict(peak_working_set_bytes=None, error='GetProcessMemoryInfo:' + str(C.get_last_error()))
        return dict(peak_working_set_bytes=int(counters.PeakWorkingSetSize), error=None)
    except BaseException as error:
        return dict(peak_working_set_bytes=None, error=type(error).__name__)

def validate_memory_observation(value):
    assert type(value) is dict and set(value) == {'peak_working_set_bytes', 'error'}
    peak, error = (value['peak_working_set_bytes'], value['error'])
    assert type(peak) is int and peak >= 0 and (error is None) or (peak is None and type(error) is str and (0 < len(error) <= 160))
    return value

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
    assert record['schema']=='staged_saved_F_runtime_handoff_probe_v2' and record['authority']=='DRAFT_NONAUTHORITATIVE'
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


def validate_census_frame(frame):
    keys = 'schema seq reason limit active start_clock snapshot_clock entered passed rejected observed inflight phase last_incomplete buckets diagnostic_error_count cache_items cache_new machinery_stage installation_seen'
    assert type(frame) is dict and set(frame) == set(keys.split()) and (frame['schema'] == 'staged_saved_F_audit_census_v5')
    assert type(frame['limit']) is int and frame['limit'] == 2048 and (type(frame['seq']) is int) and (1 <= frame['seq'] <= 20)
    assert frame['reason'] in ('begin', 'progress', 'prefix_complete', 'import_return_before2048', 'import_error_before2048')
    assert type(frame['active']) is bool and type(frame['inflight']) is bool
    assert all((type(frame[key]) is float and math.isfinite(frame[key]) for key in ('start_clock', 'snapshot_clock')))
    assert frame['snapshot_clock'] >= frame['start_clock']
    for key in ('entered', 'passed', 'rejected', 'observed'):
        assert type(frame[key]) is int and 0 <= frame[key] <= 2048
    assert frame['passed'] + frame['rejected'] <= frame['entered'] and frame['observed'] <= frame['passed']
    phases = ('identity1', 'runtime_link', 'cache', 'globals_attrs', 'ownership', 'image_digest', 'machinery')
    assert frame['phase'] in (*phases, None) and frame['last_incomplete'] in (*phases, None)
    assert type(frame['buckets']) is dict and set(frame['buckets']) == set((*phases, 'entry_total', 'audit_body_inclusive'))
    for row in frame['buckets'].values():
        assert type(row) is list and len(row) == 3 and (type(row[0]) is int) and (0 <= row[0] <= 2048)
        assert all((type(value) is float and math.isfinite(value) and (value >= 0) for value in row[1:]))
        assert row[2] <= row[1] + 1e-09
    assert type(frame['diagnostic_error_count']) is int and 0 <= frame['diagnostic_error_count'] <= 4
    assert all((type(frame[key]) is int and 0 <= frame[key] <= 4096 for key in ('cache_items', 'cache_new')))
    assert type(frame['machinery_stage']) is int and frame['machinery_stage'] in (0, 1, 2)
    assert type(frame['installation_seen']) is int and frame['installation_seen'] == 1
    if frame['reason'] == 'begin':
        assert frame['seq'] == 1 and frame['entered'] == frame['passed'] == frame['rejected'] == frame['observed'] == 0
        assert frame['active'] and (not frame['inflight']) and (frame['phase'] is None) and (frame['last_incomplete'] is None)
        assert all((row == [0, 0.0, 0.0] for row in frame['buckets'].values()))
    elif frame['reason'] == 'progress':
        assert frame['passed'] in (1, 128, 256, 384, 512, 640, 768, 896, 1024, 1152, 1280, 1408, 1536, 1664, 1792, 1920) and frame['entered'] == frame['passed'] and (frame['rejected'] == 0)
        assert frame['observed'] == frame['passed'] - 1 and frame['active'] and (not frame['inflight']) and (frame['phase'] is None)
    if frame['reason'] == 'prefix_complete':
        assert frame['entered'] == frame['passed'] == frame['observed'] == 2048 and frame['rejected'] == 0 and (not frame['active']) and (not frame['inflight'])
    elif frame['reason'] in ('import_return_before2048', 'import_error_before2048'):
        assert not frame['active'] and (not frame['inflight']) and (frame['phase'] is None) and (frame['passed'] < 2048)
        assert frame['entered'] == frame['passed'] + frame['rejected'] and frame['observed'] == frame['passed']
        if frame['reason'] == 'import_return_before2048':
            assert frame['rejected'] == 0
    return frame

def parse_diagnostic_stderr(raw):
    stages = []
    graphs = []
    other = []
    malformed = []
    census = []
    census_bytes = 0
    allowed = set(('loader_ready', 'before_adapter_import', 'adapter_import_returned', 'after_adapter_import_attempt', 'before_machinery_authentication', 'machinery_authenticated', 'before_source_bytes', 'after_source_bytes', 'before_adapter_roots', 'after_adapter_roots', 'before_final_source_bookend', 'after_final_source_bookend', 'before_retention', 'after_retention', 'before_boundary_close', 'after_boundary_close', 'before_profile', 'after_profile', 'before_finish_import', 'after_finish_import', 'before_final_runtime_close', 'after_final_runtime_close')) | {'loader_ready', 'before_adapter_import', 'after_adapter_import_attempt', 'adapter_import_returned', 'machinery_authenticated', 'before_adapter_roots', 'after_adapter_roots', 'before_boundary_close', 'after_boundary_close'}
    for line in raw.splitlines(keepends=True):
        if not line.endswith(b'\n'):
            other.append(line)
            continue
        try:
            row = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            other.append(line)
            continue
        if type(row) is list and len(row) == 2 and (row[0] == 'census'):
            validate_census_frame(row[1])
            assert len(line) <= 2048 and canonical(row) + b'\n' == line
            assert row[1]['seq'] == len(census) + 1 and len(census) < 20
            schedule = (1, 128, 256, 384, 512, 640, 768, 896, 1024, 1152, 1280, 1408, 1536, 1664, 1792, 1920)
            progress = [frame['passed'] for frame in census if frame['reason'] == 'progress']
            if row[1]['reason'] == 'progress':
                assert len(progress) < len(schedule) and row[1]['passed'] == schedule[len(progress)]
            elif row[1]['reason'] == 'prefix_complete':
                assert progress == list(schedule)
            elif row[1]['reason'] in ('import_return_before2048', 'import_error_before2048'):
                assert progress == [number for number in schedule if number <= row[1]['passed']]
            if census:
                assert row[1]['reason'] != 'begin'
                assert all((row[1][key] >= census[-1][key] for key in ('entered', 'passed', 'rejected', 'observed', 'snapshot_clock')))
                assert all((all((after >= before for after, before in zip(row[1]['buckets'][name], census[-1]['buckets'][name]))) for name in row[1]['buckets']))
                assert census[-1]['active'] and census[-1]['reason'] not in ('prefix_complete', 'import_return_before2048', 'import_error_before2048')
            else:
                assert row[1]['reason'] == 'begin' and row[1]['entered'] == row[1]['passed'] == row[1]['observed'] == 0
            census_bytes += len(line)
            assert census_bytes <= 24576
            census.append(row[1])
        elif type(row) is list and len(row) == 3 and (row[0] == 'stage') and (type(row[1]) is str) and (row[1] in allowed) and (type(row[2]) is float) and math.isfinite(row[2]):
            stages.append(row)
        elif type(row) is list and len(row) == 2 and (row[0] in ('enter', 'exit')) and (type(row[1]) is float) and math.isfinite(row[1]):
            graphs.append(row)
        else:
            malformed.append(line)
            other.append(line)
    residual = b''.join(other)
    return dict(stages=stages, graph_frames=graphs, census_frames=census, census_bytes=census_bytes, non_stage_raw_base64=base64.b64encode(residual).decode(), non_stage_pin=pin(residual), unclassified_json_lines=len(malformed), stack_present=b'Timeout (0:00:02)!' in residual and b'Thread ' in residual, stage_parse_complete=False)

def validate_exception_images(images):
    remaining=[48];observation_failure=[False]
    def visit(row,depth):
        if row is None:return
        remaining[0]-=1;assert remaining[0]>=0 and depth<=6
        assert type(row) is dict and set(row)==set(('type','message','primary','secondary','cause','group','truncated'))
        assert type(row['type']) is str and len(row['type'])<=80 and type(row['message']) is str and len(row['message'])<=180 and type(row['truncated']) is bool
        assert type(row['secondary']) is list and len(row['secondary'])<=8 and type(row['group']) is list and len(row['group'])<=8
        if row['message'].startswith(('audit census observation failed','audit census cleanup failed')):observation_failure[0]=True
        visit(row['primary'],depth+1);visit(row['cause'],depth+1)
        for child in row['group']:visit(child,depth+1)
        for child in row['secondary']:
            assert type(child) is dict and set(child)=={'layer','error'} and type(child['layer']) is str and len(child['layer'])<=80
            visit(child['error'],depth+1)
    for row in images:visit(row,0)
    return observation_failure[0]

def validate_diagnostic_record(case,stdout,child_code,identity,argv):
    record=json.loads(stdout);assert canonical(record)+b'\n'==stdout
    assert record['schema']=='staged_saved_F_runtime_handoff_probe_v2' and record['authority']=='DRAFT_NONAUTHORITATIVE'
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
    assert not validate_exception_images((record['primary'],*record['secondary']))
    kernel=record['kernel_identity'];assert (kernel['pid'],kernel['process_creation_filetime'])==(identity['pid'],identity['creation'])
    assert Path(kernel['image_path'])==EXE and kernel['command_line_sha']==pin(subprocess.list2cmdline(argv).encode('utf-8'))
    witness=record['self_handles_closed'] and calls==[1,1] and record['resource_phase']=='CLOSED' and record['dll_directory_close_returned'] and record['namespace_alias_absent']
    return record,witness

RECORD_KEYS=set(['F_launch_admitted', 'actual_F', 'authority', 'boundary_phase', 'boundary_report', 'case', 'close_calls', 'dll_directory_close_returned', 'early_audit_blocked', 'external_expected_truth_verified', 'failure_phase', 'formal_result', 'full_P1_content_verified', 'full_runtime_binding_verified', 'guard', 'import_profile', 'independent_root_verified', 'inputs_phase', 'kernel_identity', 'live_at_report', 'namespace_alias_absent', 'namespace_phase', 'native_authorized', 'native_behavior_verified', 'old_inputs_successor_matches', 'old_namespace_successor_matches', 'parent_independently_authenticated_python_object_graph', 'permit_issued', 'primary', 'production_seal', 'resource_admission', 'resource_phase', 'retained_modules', 'role_bootstrap', 'run_authority', 'runtime_is_resource_owner', 'runtime_phase', 'runtime_was_live', 'schema', 'scientific_evidence_adopted', 'secondary', 'self_handles_closed', 'source_bookends', 'source_epoch', 'source_phase', 'startup_profile', 'startup_tcb_authenticated', 'status', 'upstream_owner_verified'])
GUARD_KEYS=set(['events', 'faults', 'process_attempts', 'protected_open_attempts', 'sentinel', 'source_open_attempts', 'write_attempts'])
BOUNDARY_KEYS=set(['actual_F', 'actual_filesystem_alias_verified', 'arbitrary_native_effects_verified', 'audit_handoff_observed', 'authority', 'baseline_root_authenticated', 'blocked_optional_attempts', 'callback_retained', 'cold_main_self_anchor_verified', 'fault_kind', 'finder_behavior_closure_verified', 'finder_function_metadata_bookend_verified', 'finder_function_mutation_guard_installed', 'finder_registry_contents_verified', 'forced_numpy_SVE_false', 'formal_result', 'full_P1_content_verified', 'full_runtime_binding_verified', 'hook_active', 'hook_installation_observed', 'import_boundary_completed', 'independent_root_verified', 'installation_sentinel_observed', 'internal_introspection_events', 'machinery_authenticated_stage', 'machinery_authentication_pending', 'machinery_observed_stage', 'optional_Popen_attempts', 'permit_issued', 'phase', 'resource_admission', 'role_bootstrap', 'run_authority', 'schema', 'scientific_evidence_adopted', 'source49_bookend_equal', 'source49_expected_truth_bound_by_import_boundary', 'unobserved_RAM_ABA_verified', 'violations'])
BOUNDARY_FALSE=('hook_active', 'finder_registry_contents_verified', 'finder_behavior_closure_verified', 'unobserved_RAM_ABA_verified', 'baseline_root_authenticated', 'source49_expected_truth_bound_by_import_boundary', 'cold_main_self_anchor_verified', 'independent_root_verified', 'full_runtime_binding_verified', 'actual_filesystem_alias_verified', 'arbitrary_native_effects_verified', 'full_P1_content_verified', 'role_bootstrap', 'permit_issued', 'actual_F', 'run_authority', 'scientific_evidence_adopted', 'resource_admission', 'formal_result')


def validate_prefix_record(record, reason='prefix_complete'):
    assert type(record) is dict and set(record) == RECORD_KEYS
    assert record['schema'] == 'staged_saved_F_runtime_handoff_probe_v2' and record['authority'] == 'DRAFT_NONAUTHORITATIVE'
    assert record['case'] == 'import_discovery' and record['source_epoch'] == SOURCE_SHA
    assert all((record[k] is False for k in FALSE_FIELDS)) and record['live_at_report'] is False
    assert record['status'] == 'failed' and record['failure_phase'] == 'IMPORT' and (record['startup_profile'] is None) and (record['import_profile'] is None)
    assert record['runtime_phase'] == 'UNRESOLVED' and record['boundary_phase'] == 'FAULTED' and (record['resource_phase'] == 'CLOSED') and (record['runtime_was_live'] is False)
    assert record['source_phase'] == record['inputs_phase'] == record['namespace_phase'] == 'CONSUMED'
    assert all((record[k] is True for k in ('runtime_is_resource_owner', 'old_inputs_successor_matches', 'old_namespace_successor_matches', 'self_handles_closed', 'dll_directory_close_returned', 'namespace_alias_absent')))
    assert record['close_calls'] == [1, 1] and all((type(v) is int for v in record['close_calls']))
    assert type(record['retained_modules']) is int and record['retained_modules'] == 0 and (type(record['source_bookends']) is int) and (record['source_bookends'] >= 2)
    assert record['early_audit_blocked'] == []
    guard = record['guard']
    assert type(guard) is dict and set(guard) == GUARD_KEYS
    assert type(guard['source_open_attempts']) is int and guard['source_open_attempts'] > 0
    assert type(guard['sentinel']) is int and guard['sentinel'] == 1 and (guard['faults'] == [])
    assert all((type(guard[k]) is int and guard[k] == 0 for k in ('protected_open_attempts', 'write_attempts', 'process_attempts')))
    assert type(guard['events']) is list and all((type(v) is str for v in guard['events']))
    assert guard['events'].index('self_handles_live') < guard['events'].index('source_read_begin') < guard['events'].index('transfer_committed') < guard['events'].index('self_handles_closed')
    report = record['boundary_report']
    assert type(report) is dict and set(report) == BOUNDARY_KEYS
    fixed = dict(schema='staged_saved_F_successor_import_boundary_report_v1', authority='DRAFT_NONAUTHORITATIVE', phase='FAULTED', audit_handoff_observed=1, installation_sentinel_observed=1, violations=0, machinery_authenticated_stage=0, fault_kind='')
    assert all((type(report[k]) is type(v) and report[k] == v for k, v in fixed.items()))
    assert all((report[k] is False for k in BOUNDARY_FALSE))
    assert all((report[k] is True for k in ('callback_retained', 'hook_installation_observed', 'finder_function_mutation_guard_installed')))
    for k in ('forced_numpy_SVE_false', 'finder_function_metadata_bookend_verified', 'source49_bookend_equal', 'import_boundary_completed', 'hook_active'):
        assert report[k] is False
    assert type(report['machinery_observed_stage']) is int and report['machinery_observed_stage'] in (0, 1, 2)
    assert report['machinery_authentication_pending'] is (report['machinery_observed_stage'] != report['machinery_authenticated_stage'])
    assert type(report['internal_introspection_events']) is int and 0 <= report['internal_introspection_events'] <= 4096
    assert type(report['optional_Popen_attempts']) is int and type(report['blocked_optional_attempts']) is int
    assert report['optional_Popen_attempts'] == report['blocked_optional_attempts'] and report['optional_Popen_attempts'] in (0, 1)
    assert not validate_exception_images((record['primary'], *record['secondary']))
    assert reason in ('prefix_complete', 'import_return_before2048')
    expected = 'diagnostic_prefix_complete_2048' if reason == 'prefix_complete' else 'diagnostic_import_return_before2048'
    assert record['primary']['type'] == 'AuditCensusStop' and record['primary']['message'] == expected
    return True

def validate_prefix_stderr(raw):
    parsed = parse_diagnostic_stderr(raw)
    frames = parsed['census_frames']
    assert frames
    final = frames[-1]
    reason = final['reason']
    assert reason in ('prefix_complete', 'import_return_before2048')
    names = ['loader_ready', 'before_adapter_import'] + (['adapter_import_returned'] if reason == 'import_return_before2048' else []) + ['after_adapter_import_attempt']
    assert [row[1] for row in parsed['stages']] == names
    schedule = (1, 128, 256, 384, 512, 640, 768, 896, 1024, 1152, 1280, 1408, 1536, 1664, 1792, 1920)
    count = final['passed']
    assert count == 2048 if reason == 'prefix_complete' else 0 <= count < 2048
    assert [f['passed'] for f in frames] == [0, *[n for n in schedule if n <= count], count]
    assert not any((f['diagnostic_error_count'] or f['rejected'] or f['inflight'] or (f['phase'] is not None) or (f['last_incomplete'] is not None) for f in frames))
    begin = frames[0]
    assert begin['cache_new'] == 0
    for frame in frames:
        assert frame['start_clock'] == begin['start_clock'] and frame['cache_new'] == frame['cache_items'] - begin['cache_items']
        assert all((row[0] == frame['passed'] for row in frame['buckets'].values()))
    assert all((b['machinery_stage'] >= a['machinery_stage'] for a, b in zip(frames, frames[1:])))
    assert base64.b64decode(parsed['non_stage_raw_base64']) == b'' and (not parsed['unclassified_json_lines']) and (not parsed['stack_present'])
    graphs = parsed['graph_frames']
    assert 2 <= len(graphs) <= 256 and len(graphs) % 2 == 0
    assert [row[0] for row in graphs] == ['enter', 'exit'] * (len(graphs) // 2)
    times = []
    graph_bytes = 0
    for line in raw.splitlines(keepends=True):
        row = json.loads(line)
        assert canonical(row) + b'\n' == line
        times.append(row[1]['snapshot_clock'] if row[0] == 'census' else row[-1])
        if row[0] in ('enter', 'exit'):
            graph_bytes += len(line)
    assert graph_bytes <= 16384 and all((b >= a for a, b in zip(times, times[1:])))
    return parsed

def validate_prefix_observation(record, raw):
    parsed = validate_prefix_stderr(raw)
    reason = parsed['census_frames'][-1]['reason']
    validate_prefix_record(record, reason)
    assert parsed['census_frames'][-1]['machinery_stage'] == record['boundary_report']['machinery_observed_stage']
    return parsed

def prefix_terminal_complete(result, drain_reason):
    if drain_reason is not None or type(result) is not dict:
        return False
    return result.get('finite_terminal_complete') is True and result.get('self_close_witness_present') is True and (result.get('child_record') is not None)

def compare_child(case, code, stdout, stderr, child_code, identity, argv, writer_errors):
    if case == 'discovery':
        return base_compare_child(case, code, stdout, stderr, child_code, identity, argv, writer_errors)
    parsed = parse_diagnostic_stderr(stderr)
    assert parsed['stages'] and any((row[1] == 'before_adapter_import' for row in parsed['stages'])) and (not writer_errors)
    assert parsed['census_frames'] and (not any((row['diagnostic_error_count'] for row in parsed['census_frames']))) and (not parsed['stack_present'])
    record, witness = (None, False) if not stdout else validate_diagnostic_record(case, stdout, child_code, identity, argv)
    reason = parsed['census_frames'][-1]['reason']
    finite = False
    if record is not None:
        assert record['status'] == 'failed' and record['primary'] is not None
        if reason in ('prefix_complete', 'import_return_before2048'):
            validate_prefix_observation(record, stderr)
            finite = True
        else:
            assert reason == 'import_error_before2048'
    return dict(child_record=record, diagnostic=parsed, self_close_witness_present=witness, adapter_import_attempts_upper_bound=1, adapter_import_return_observed=any((row[1] == 'adapter_import_returned' for row in parsed['stages'])), prefix_complete=reason == 'prefix_complete', finite_terminal_complete=finite, census_terminal_reason=reason if record is not None else 'no_child_report_after_' + reason, diagnostic_only=True)

def one_case(case,seconds):
    started=time.perf_counter();code=plan=expected=actual=argv=api=None
    process=writer=None;writer_errors=[];released=[False];stdin_closed=[False]
    stdout=stderr=b'';child_code=identity=observation=None;closed=False;primary=None;cleanup=[];result=memory=drain_reason=None
    context_before=context_after=None
    try:
        code=transport(); plan=manifest(case,code); expected=canonical(plan); plan_path=OUT/('probe_'+case+'.plan.json')
        if case=='path':plan['initial_paths']=[str(ROOT),*plan['initial_paths'][1:]];expected=canonical(plan)
        actual=expected if case!='manifest_flip' else expected[:-1]+b'!'
        with plan_path.open('xb') as stream:stream.write(actual)
        argv=[str(EXE),'-P','-B','-s','-S','-c',code.decode('utf-8'),'--pre-entry-lease',str(plan_path),pin(expected)['sha256']]
        if case=='flags':argv.remove('-P')
        assert len(subprocess.list2cmdline(argv).encode('utf-16-le'))//2<=30000
        env=dict(plan['environment'])
        if case=='environment':env['OMP_NUM_THREADS']='2'
        assert pin(DRAIN.read_bytes())=={'bytes': 14253, 'sha256': 'e0c54dc42657c223a81e7df8e2316289de58f95ce60457080b27fdf52931bc2d'}
        drain=load(DRAIN,'pre_entry_fixed_drain');drain.STDOUT_CAP=131072;drain.STDERR_CAP=32768
        checker=drain.check_bindings;held=drain.drain
        checker_proof=(checker.__code__,checker.__defaults__,checker.__kwdefaults__,checker.__closure__)
        held_proof=(held.__code__,held.__defaults__,held.__kwdefaults__,held.__closure__,tuple(c.cell_contents for c in held.__closure__ or ()))
        def check_drain():
            assert drain.check_bindings is checker and all(a is b for a,b in zip((checker.__code__,checker.__defaults__,checker.__kwdefaults__,checker.__closure__),checker_proof))
            assert drain.drain is held and all(a is b for a,b in zip((held.__code__,held.__defaults__,held.__kwdefaults__,held.__closure__),held_proof[:4]))
            assert all(c.cell_contents is expected for c,expected in zip(held.__closure__ or (),held_proof[4]))
            checker()
        check_drain()
        api=process_api()
        from types import SimpleNamespace
        context_before=POST.context(SimpleNamespace(**globals()),case,code,argv)[2]
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
        child_code,stdout,stderr,error,observation=held(process,seconds-(time.perf_counter()-started)-0.5)
        drain_reason=error
        check_drain()
        drain.validate_guard(observation['memory_guard'],healthy=error is None)
        if writer is not None:writer.join(.5)
        else:process.stdin.close();stdin_closed[0]=True
        assert writer is None or not writer.is_alive()
        assert observation['pipes_closed'] and observation['reader_threads_terminal'] and not observation['cleanup'] and not observation['reader_errors']
        assert not observation['stdout_truncated'] and not observation['stderr_truncated']
        if case in ('import_discovery','normal'):assert error in (None,'timeout','memory_limit','memory_observation_failed','memory_sample_limit')
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
            guard=None if observation is None else observation.get('memory_guard')
            memory=(dict(peak_working_set_bytes=guard['maxima']['child']['peak_working_set_bytes'],error=None)
                if guard is not None and guard['samples']>0 else dict(peak_working_set_bytes=None,error='no_live_memory_observation'))
            try:
                handle=int(process._handle);process._handle.Close();flags=W.DWORD();C.set_last_error(0)
                closed=process._handle.closed and not api.GetHandleInformation(W.HANDLE(handle),C.byref(flags)) and C.get_last_error()==6
            except BaseException as error:cleanup.append('process_handle:'+type(error).__name__)
    if case in ('discovery','import_discovery') and primary is None:
        if not POST.terminal_complete(result,drain_reason):primary='post_return_observation_incomplete'
    if process is not None:
        try:validate_memory_observation(memory)
        except BaseException as error:cleanup.append('memory_schema:'+type(error).__name__)
    if context_before is not None:
        try:
            from types import SimpleNamespace
            context_after=POST.context(SimpleNamespace(**globals()),case,code,argv)[2]
            assert context_after==context_before
        except BaseException as error:cleanup.append('reference_bookend:'+type(error).__name__)
    record=dict(schema='staged_saved_F_construction_parent_receipt_v1',context_before=context_before,context_after=context_after,profile_publication=None,authority='DRAFT_NONAUTHORITATIVE',case=case,accepted=primary is None and not cleanup and closed and stdin_closed[0],
        charged_seconds=time.perf_counter()-started,cap_seconds=seconds,primary=primary,cleanup=cleanup,result=result,
        plan_pin=None if actual is None else pin(actual),expected_manifest_pin=None if expected is None else pin(expected),transport_pin=None if code is None else pin(code),child_exit=child_code,parent_kernel_identity=identity,parent_controller_pid=os.getpid(),
        release_sent=released[0],writer_errors=writer_errors,writer_thread_terminal=writer is None or not writer.is_alive(),stdin_closed=stdin_closed[0],
        parent_process_handle_closed=closed,bounded_drain=observation,memory_observation=memory,memory_observation_source='last_live_memory_guard',drain_reason=drain_reason,stdout_pin=pin(stdout),stderr_pin=pin(stderr),
        stdout_raw_base64=base64.b64encode(stdout).decode(),stderr_raw_base64=base64.b64encode(stderr).decode(),
        **{k:False for k in FALSE_FIELDS})
    record['accepted']=record['accepted'] and record['charged_seconds']<=seconds
    from types import SimpleNamespace
    POST.finalize_profile(SimpleNamespace(**globals()),record,started,seconds,time.perf_counter)
    if case in ('discovery','import_discovery','normal'): save(OUT/('probe_'+case+'.receipt.json'),record)
    else:
        journal=OUT/'probe_cases.receipts.jsonl'
        prior=[] if not journal.exists() else [json.loads(line) for line in journal.read_bytes().splitlines()]
        if journal.exists(): assert journal.read_bytes()==b''.join(canonical(row)+b'\n' for row in prior)
        order=('normal','precommit','postcommit','blocked_installation','handoff_middle','M_only','after_D')
        assert [row['case'] for row in prior]==list(order[:order.index(case)])
        with journal.open('ab' if prior else 'xb') as stream: stream.write(canonical(record)+b'\n')
    return record


POST=load(ROOT/'experiments/staged_rts24_saved_fresh_construction_validation_v1.py','_post_return_validation')
def compare_child(case,code,stdout,stderr,child_code,identity,argv,writer_errors):
    from types import SimpleNamespace
    return POST.compare(SimpleNamespace(**globals()),case,code,stdout,stderr,child_code,identity,argv,writer_errors)

REFERENCE=load(ROOT/'experiments/staged_rts24_saved_fresh_live_profile_reference_v1.py','_live_frozen_profile_reference')

TRANSPORT=load(ROOT/'experiments/staged_rts24_saved_fresh_utf16_transport_v1.py','_registered_xz_transport')


def validate_manifest_pair(plan,code):
    core=load(CORE,'_paired_manifest_core')
    assert core.check_plan(canonical(plan))==plan and plan['bootstrap_pin']==pin(code)
    assert plan['case'] in ('discovery','import_discovery')
    for key,path in (('namespace_helper',ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v3.py'),
            ('import_helper',ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v4.py'),('import_policy',OUT/'import_policy.json')):
        expected=dict(path=str(path),pin=pin(path.read_bytes()))
        assert plan[key]==expected and core.read_file(path,plan[key]['pin'])==path.read_bytes()
    assert plan['producer_helpers']==producer_references() and plan['graph_contract']==construction_graph_contract()
    for ref in plan['producer_helpers'].values():core.read_file(ref['path'],ref['pin'])
    if plan['case']=='import_discovery':
        assert plan['startup_profile']==dict(path=str(OUT/'startup_profile.json'),pin=pin((OUT/'startup_profile.json').read_bytes()))
        assert plan['import_profile'] is None
    else:assert plan['startup_profile'] is plan['import_profile'] is None
    return plan


def producer_helper_paths():
    return dict(bootstrap_loader=str(ROOT/'experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v2.py'),
        construction=str(ROOT/'experiments/staged_rts24_saved_fresh_producer_bootstrap_v4.py'),
        project_graph=str(ROOT/'experiments/staged_rts24_saved_fresh_producer_project_graph_v3.py'),
        lifecycle=str(ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v3.py'),
        utilities=str(ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v1.py'),
        capture=str(ROOT/'experiments/staged_rts24_saved_fresh_prebound_expectation_code_v3.py'),
        predecessor_checkpoint=str(ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v12_non_authoritative/checkpoint.json'),
        predecessor_registration=str(ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v12_non_authoritative/registration.json'))


def producer_references():
    return {key:dict(path=path,pin=pin(Path(path).read_bytes())) for key,path in producer_helper_paths().items()}


def construction_graph_contract():
    return {'schema': 'staged_saved_F_construction_graph_contract_v1', 'calls': 43, 'kinds': {'namespace': 33, 'adapter': 10}, 'intervals': {'<before_loader_ready>': ['namespace', 'namespace', 'namespace', 'namespace', 'namespace', 'namespace', 'namespace', 'namespace', 'namespace', 'namespace', 'namespace', 'namespace', 'namespace', 'namespace', 'namespace', 'namespace', 'namespace', 'namespace', 'namespace'], 'loader_ready': ['namespace', 'namespace'], 'after_adapter_import_attempt': ['namespace', 'namespace', 'namespace', 'namespace', 'namespace'], 'before_source_bytes': ['namespace'], 'before_adapter_roots': ['adapter'], 'before_boundary_close': ['adapter', 'adapter'], 'before_profile': ['adapter'], 'before_finish_import': ['namespace', 'adapter', 'adapter', 'namespace', 'adapter', 'namespace', 'adapter'], 'after_finish_import': ['namespace', 'adapter'], 'before_final_runtime_close': ['namespace', 'adapter', 'namespace']}}
