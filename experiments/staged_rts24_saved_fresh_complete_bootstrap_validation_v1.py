"""Complete bootstrap data relations after retained child quiet; no execution authority."""
import base64
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
from types import SimpleNamespace
import os
from threading import get_ident
import zlib

GRAPH_CALL_CAP=256
GRAPH_IMAGE_CAP=4194304
STDOUT_CAP=327681
STDERR_CAP=131072
# A stop cap is not an exact successful DAG. New source is required to close it.
_EXACT_CONTRACTS=(('discovery',()),('import_discovery',None),('producer',None))
_PROFILE_ACCEPTED_ANCHOR=None
ACTOR_FALSE=('external_permission_verified','parent_independent_P1_verified','role_bootstrap','permit_issued',
    'F_launch_admitted','full_P1_content_verified','independent_root_verified','native_authorized','production_seal',
    'startup_tcb_authenticated','parent_python_graph_attested','full_runtime_binding_verified',
    'run_authority','resource_admission','scientific_evidence_adopted','formal_result','actual_F')



STAGES=('loader_ready','before_adapter_import','adapter_import_returned','after_adapter_import_attempt',
    'before_machinery_authentication','machinery_authenticated','before_source_bytes','after_source_bytes',
    'before_adapter_roots','after_adapter_roots','before_final_source_bookend','after_final_source_bookend',
    'before_retention','after_retention','before_boundary_close','after_boundary_close','before_profile','after_profile',
    'before_finish_import','after_finish_import','before_final_runtime_close','after_final_runtime_close')

METRICS=('authenticate','finder_check','adapter_check','profile')

FLAGS=('external_expected_truth_verified','upstream_owner_verified','startup_tcb_authenticated','independent_root_verified',
    'native_behavior_verified','parent_independently_authenticated_python_object_graph','full_runtime_binding_verified',
    'full_P1_content_verified','role_bootstrap','permit_issued','native_authorized','F_launch_admitted','actual_F','run_authority',
    'scientific_evidence_adopted','resource_admission','formal_result','production_seal')

CONSTRUCTION_FALSE=('initial_project_state_authenticated','independent_tcb_authenticated','producer_capability_verified',
    'full_runtime_binding_verified','full_P1_content_verified','role_bootstrap','permit_issued','run_authority',
    'resource_admission','scientific_evidence_adopted','formal_result','actual_F','unobserved_RAM_ABA_verified')

GRAPH_FALSE=tuple(name for name in CONSTRUCTION_FALSE if name!='unobserved_RAM_ABA_verified')

NAMESPACE_KEYS=set(('schema authority runtime_phase cleanup_started failure_absent resource_phase resource_owner_same pending '
    'namespace_phase namespace_same peer_same source_same inputs_phase successor_same resource_same registry_same '
    'reference_registered actual_key_absent reference_key_absent actual_aliases reference_aliases').split())

GUARD_KEYS=set(['events', 'faults', 'process_attempts', 'protected_open_attempts', 'sentinel', 'source_open_attempts', 'write_attempts'])

BOUNDARY_KEYS=set(['actual_F', 'actual_filesystem_alias_verified', 'arbitrary_native_effects_verified', 'audit_handoff_observed', 'authority', 'baseline_root_authenticated', 'blocked_optional_attempts', 'callback_retained', 'cold_main_self_anchor_verified', 'fault_kind', 'finder_behavior_closure_verified', 'finder_function_metadata_bookend_verified', 'finder_function_mutation_guard_installed', 'finder_registry_contents_verified', 'forced_numpy_SVE_false', 'formal_result', 'full_P1_content_verified', 'full_runtime_binding_verified', 'hook_active', 'hook_installation_observed', 'import_boundary_completed', 'independent_root_verified', 'installation_sentinel_observed', 'internal_introspection_events', 'machinery_authenticated_stage', 'machinery_authentication_pending', 'machinery_observed_stage', 'optional_Popen_attempts', 'permit_issued', 'phase', 'resource_admission', 'role_bootstrap', 'run_authority', 'schema', 'scientific_evidence_adopted', 'source49_bookend_equal', 'source49_expected_truth_bound_by_import_boundary', 'unobserved_RAM_ABA_verified', 'violations'])

def require(value,message):
    if not value:raise ValueError(message)

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')

def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())

def unique_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'duplicate JSON key');result[key]=value
        return result
    def invalid(value):raise ValueError('nonfinite JSON value')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)

def checked_pin(value,cap):
    require(type(value) is dict and set(value)=={'bytes','sha256'},'closed pin required')
    require(type(value['bytes']) is int and 0<=value['bytes']<=cap and type(value['sha256']) is str
        and len(value['sha256'])==64 and all(c in '0123456789abcdef' for c in value['sha256']),'bounded pin required')
    return value

def uint(value,cap=2**64-1):return type(value) is int and 0<=value<=cap

def profile_shape(profile):
    keys={'schema','authority','modules','cache','paths','finder_types','machinery_observed','machinery_authenticated',
        'optional_attempts','loaded_python_graph_attested','registry_contents_verified','native_behavior_verified'}
    assert type(profile) is dict and set(profile)==keys
    assert profile['schema']=='staged_saved_F_B_S_import_observation_v1' and profile['authority']=='DRAFT_NONAUTHORITATIVE'
    for key,value in (('machinery_observed',2),('machinery_authenticated',2),('optional_attempts',1)):assert type(profile[key]) is int and profile[key]==value
    for key in ('loaded_python_graph_attested','registry_contents_verified','native_behavior_verified'):assert profile[key] is False
    for key in ('modules','cache','paths','finder_types'):assert type(profile[key]) is list
    assert 0<len(profile['modules'])<=4096 and 0<len(profile['cache'])<=4096 and len(profile['paths'])==6 and 0<len(profile['finder_types'])<=16
    for row in profile['modules']:
        assert type(row) is list and len(row) in (3,5) and type(row[0]) is str and row[0]
        if row[1]=='module':assert len(row)==5 and all(v is None or type(v) is str for v in row[2:4]) and type(row[4]) is str and row[4]
        else:assert row[1]=='opaque' and len(row)==3 and type(row[2]) is str and row[2]
    for row in profile['cache']:assert type(row) is list and len(row)==2 and all(type(v) is str and v for v in row)
    for key in ('modules','cache'):
        names=[row[0] for row in profile[key]];assert names==sorted(set(names))
    for key in ('paths','finder_types'):assert all(type(v) is str and v for v in profile[key])
    return profile

def namespace_shape(value,success=False):
    require(type(value) is dict and set(value)==NAMESPACE_KEYS,'closed namespace terminal fields required')
    require(value['schema']=='staged_saved_F_namespace_terminal_observation_v1'
        and value['authority']=='DRAFT_NONAUTHORITATIVE','namespace terminal schema differs')
    booleans=NAMESPACE_KEYS-set('schema authority runtime_phase resource_phase namespace_phase inputs_phase pending actual_aliases reference_aliases'.split())
    require(all(type(value[key]) is bool for key in booleans),'namespace terminal boolean type differs')
    require(type(value['pending']) is list and len(value['pending'])==2 and all(type(item) is bool for item in value['pending']),
        'two native pending flags required')
    for key in ('actual_aliases','reference_aliases'):
        rows=value[key];require(type(rows) is list and len(rows)<=4096 and all(type(v) is str and len(v)<=4096 for v in rows)
            and rows==sorted(set(rows)),'bounded namespace alias list required')
    require(all(value[key] is None or type(value[key]) is str for key in ('runtime_phase','resource_phase','namespace_phase','inputs_phase')),
        'namespace terminal phase type differs')
    if success:
        require(value['runtime_phase']==value['resource_phase']=='CLOSED'
            and value['namespace_phase']==value['inputs_phase']=='CONSUMED','namespace/runtime terminal phases differ')
        require(all(value[key] is True for key in booleans-{'reference_registered'}),'namespace ownership chain is incomplete')
        require(value['reference_registered'] is False and value['pending']==[False,False]
            and value['actual_aliases']==value['reference_aliases']==[],'namespace aliases or pending handles remain')
    return value

def construction_shape(value):
    keys=set(CONSTRUCTION_FALSE)|{'schema','authority','source_modules','loader_execs','entry_execs','graph','P1_reads','admission_present'}
    require(type(value) is dict and set(value)==keys,'closed construction fields required')
    require(value['schema']=='staged_saved_F_unadmitted_project_construction_v1' and value['authority']=='DRAFT_NONAUTHORITATIVE',
        'unadmitted construction schema differs')
    require(all(value[key] is False for key in CONSTRUCTION_FALSE) and value['admission_present'] is False,'construction authority differs')
    for key,expected in (('source_modules',37),('loader_execs',36),('entry_execs',2),('P1_reads',0)):
        require(type(value[key]) is int and value[key]==expected,'construction count differs: '+key)
    graph=value['graph'];keys=set(GRAPH_FALSE)|{'schema','authority','modules','nodes','graph_pin','structure_and_identity_stable'}
    require(type(graph) is dict and set(graph)==keys,'closed project graph observation required')
    require(graph['schema']=='staged_saved_F_project_continuity_observation_v1' and graph['authority']=='DRAFT_NONAUTHORITATIVE',
        'project graph schema differs')
    require(all(graph[key] is False for key in GRAPH_FALSE) and graph['structure_and_identity_stable'] is True,'project graph authority differs')
    require(type(graph['modules']) is int and graph['modules']==37 and type(graph['nodes']) is int and 1<=graph['nodes']<=50000,
        'project graph size differs')
    require(type(graph['graph_pin']) is list and len(graph['graph_pin'])==2,'serialized project graph pin required')
    checked_pin(dict(bytes=graph['graph_pin'][0],sha256=graph['graph_pin'][1]),8388608)
    return value

def profile_data(encoded):
    require(type(encoded) is dict and set(encoded)=={'encoding','raw_pin','data'}
        and encoded['encoding']=='zlib_base64' and type(encoded['data']) is str,'closed compressed profile required')
    checked_pin(encoded['raw_pin'],1048576)
    packed=base64.b64decode(encoded['data'],validate=True);unpacker=zlib.decompressobj()
    raw=unpacker.decompress(packed,1048577)
    require(len(raw)<=1048576 and unpacker.eof and not unpacker.unconsumed_tail and not unpacker.unused_data
        and pin(raw)==encoded['raw_pin'],'complete bounded profile stream required')
    profile=unique_json(raw);require(canonical(profile)==raw,'canonical import profile required')
    return profile_shape(profile)

def kernel_match(parent,record,identity,argv):
    row=record['kernel_identity']
    keys={'pid','tid','process_creation_filetime','thread_creation_filetime','image_path','command_line_sha'}
    require(type(row) is dict and set(row)==keys,'closed child kernel observation required')
    require(type(identity) is dict and set(identity)=={'pid','creation','image_path'},'retained parent kernel observation required')
    require(all(uint(row[k]) and row[k]>0 for k in ('pid','tid','process_creation_filetime','thread_creation_filetime')),
        'exact kernel integer fields required')
    require(uint(identity['pid']) and uint(identity['creation']) and identity['pid']>0 and identity['creation']>0,
        'exact parent kernel integer fields required')
    require((row['pid'],row['process_creation_filetime'])==(identity['pid'],identity['creation'])
        and Path(row['image_path'])==Path(identity['image_path'])==parent.EXE,'same retained process/image required')
    require(row['command_line_sha']==pin(subprocess.list2cmdline(argv).encode('utf8')),'kernel command binding differs')
    return True

def startup_shape(parent,profile,plan,code):
    keys=set(('schema conditional_tcb_assumption_id bootstrap_pin environment_sha cwd paths initial_modules ordered_import_events '
        'module_origins disk_file_observations native_origin_boundaries initial_runtime_opens startup_tcb_authenticated '
        'loaded_python_graph_attested native_behavior_verified').split())
    require(type(profile) is dict and set(profile)==keys,'closed startup profile required')
    require(profile['schema']=='staged_saved_F_conditional_startup_profile_v1'
        and profile['conditional_tcb_assumption_id']=='controlled_compute_CPython_3_12_12_windows_vm_stdlib_native_kernel_v1',
        'startup schema/conditional TCB differs')
    require(profile['bootstrap_pin']==pin(code) and profile['environment_sha']==pin(canonical(plan['environment']))
        and profile['cwd']==str(parent.ROOT) and profile['paths']==plan['initial_paths'],'startup source/environment binding differs')
    for key in ('startup_tcb_authenticated','loaded_python_graph_attested','native_behavior_verified'):
        require(profile[key] is False,'startup authority differs')
    for key,cap in (('initial_modules',4096),('ordered_import_events',2048),('module_origins',4096),
            ('native_origin_boundaries',1024),('initial_runtime_opens',4096)):
        require(type(profile[key]) is list and len(profile[key])<=cap,'startup list cap differs')
    for key in ('initial_modules','module_origins'):
        rows=profile[key]
        require(rows and all(type(row) is list and len(row)==3 and type(row[0]) is str and 0<len(row[0])<=4096
            and (row[1] is None or type(row[1]) is str and len(row[1])<=4096)
            and type(row[2]) is str and 0<len(row[2])<=4096 for row in rows),'startup module rows differ')
        require([row[0] for row in rows]==sorted(set(row[0] for row in rows)),'startup module names differ')
    for row in profile['ordered_import_events']:
        require(type(row) is list and len(row)==2 and type(row[0]) is str and 0<len(row[0])<=4096
            and (row[1] is None or type(row[1]) is str and len(row[1])<=4096),'startup import row differs')
        require(not any(row[0]==name or row[0].startswith(name+'.')
            for name in ('src','experiments','tests','numpy','scipy','pyomo','highspy')),'startup imported a protected module')
    for key in ('native_origin_boundaries','initial_runtime_opens'):
        require(all(type(value) is str and 0<len(value)<=4096 and Path(value).is_absolute() for value in profile[key]),
            'startup origin path differs')
    require(profile['native_origin_boundaries'] and profile['native_origin_boundaries']==sorted(profile['native_origin_boundaries'],key=str.casefold),
        'startup native origins differ')
    require(all(Path(path).is_relative_to(parent.RUNTIME) for path in profile['initial_runtime_opens']),
        'startup runtime open escaped distribution')
    files=profile['disk_file_observations'];require(type(files) is dict and len(files)<=128,'startup disk set cap')
    require(sum(checked_pin(value,8388608)['bytes'] for value in files.values())<=33554432,'startup disk aggregate cap')
    core=parent.load(parent.CORE,'_construction_startup_readback')
    for path,value in files.items():
        require(type(path) is str and Path(path).is_absolute() and Path(path).is_relative_to(parent.RUNTIME),'controlled startup origin required')
        core.read_file(path,value,links=True)
    return profile

def permission_shape(value,success=False):
    flags=('external_permission_verified','full_P1_content_verified','independent_root_verified','role_bootstrap',
        'permit_issued','run_authority','F_launch_admitted','actual_F','resource_admission','scientific_evidence_adopted','formal_result')
    keys=set(flags)|{'schema','authority','issuer_phase','guard_phase','installed','counters','faults','admission_present'}
    require(type(value) is dict and set(value)==keys and value['schema']=='staged_saved_F_P1_permission_observation_v1'
        and value['authority']=='DRAFT_NONAUTHORITATIVE','closed permission observation required')
    require(all(value[key] is False for key in flags) and value['admission_present'] is False,'no P1 permission is issued')
    require(type(value['installed']) is bool and value['issuer_phase'] in ('DISABLED','RETIRED','UNRESOLVED')
        and value['guard_phase'] in ('NEW','INSTALLED_DENY','DENY','CLOSED'),'disabled permission phases required')
    counts=value['counters'];require(type(counts) is dict and set(counts)=={'selected','protected','allowed','writes','processes','mutations','construction_reads','runtime_reads','outside_reads'}
        and all(type(number) is int and 0<=number<=16384 for number in counts.values()),'bounded permission counters required')
    require(counts['allowed']==0 and type(value['faults']) is list and len(value['faults'])<=4
        and all(type(item) is str and len(item)<=96 for item in value['faults']),'zero authorized P1 reads required')
    if success:
        require(value['issuer_phase']=='DISABLED' and value['guard_phase']=='CLOSED' and value['installed'] is True
            and value['faults']==[] and all(counts[key]==0 for key in ('protected','writes','processes','mutations','outside_reads')),
            'clean continuous deny guard terminal required')
    return value

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

def parse(parent,raw):
    assert type(raw) is bytes and len(raw)<=STDERR_CAP
    normalized=[];frames=[];pending=None;calls=0;previous=-1.0;stage='<before_loader_ready>';intervals={};census_stages=[]
    for line in raw.splitlines(keepends=True):
        try:row=unique_json(line)
        except (ValueError,UnicodeDecodeError):normalized.append(line);continue
        if type(row) is not list or not row:normalized.append(line);continue
        if row[0] in ('stage','census'):
            assert parent.canonical(row)+b'\n'==line and pending is None
            if row[0]=='stage':
                assert len(row)==3 and row[1] in STAGES
                clock=row[2];stage=row[1]
            else:
                assert len(row)==2 and type(row[1]) is dict
                clock=row[1]['snapshot_clock']
                if not census_stages or census_stages[-1]!=stage:census_stages.append(stage)
            assert type(clock) is float and math.isfinite(clock) and 0<=clock and previous<=clock<=1e12
            previous=clock;normalized.append(line);continue
        if row[0]!='graph':normalized.append(line);continue
        assert parent.canonical(row)+b'\n'==line and len(row) in (5,8)
        _,seq,kind,state,clock,*sizes=row
        assert type(seq) is int and 1<=seq<=GRAPH_CALL_CAP and kind in ('namespace','adapter')
        assert type(clock) is float and math.isfinite(clock) and 0<=clock and previous<=clock<=1e12
        previous=clock
        if state=='enter':
            assert len(row)==5 and pending is None and seq==calls+1
            pending=(seq,kind,clock);calls+=1
        else:
            assert state=='exit' and len(row)==8 and pending is not None and (seq,kind)==pending[:2] and clock>=pending[2]
            assert sizes==[None,None,None] or all(type(n) is int and n>=0 for n in sizes)
            if sizes!=[None,None,None]:assert 1<=sizes[0]<=50000 and sizes[1]==sizes[0] and 1<=sizes[2]<=GRAPH_IMAGE_CAP
            intervals.setdefault(stage,[]).append(kind)
            pending=None
        frames.append(row);normalized.append(parent.canonical([state,clock])+b'\n')
    parsed=parent.parse_diagnostic_stderr(b''.join(normalized))
    parsed['graph_frames']=frames
    parsed['graph_complete']=pending is None
    parsed['graph_counts']={kind:sum(r[2]==kind and r[3]=='exit' and r[5] is not None for r in frames) for kind in ('namespace','adapter')}
    parsed['stage_parse_complete']=parsed['unclassified_json_lines']==0 and parsed['non_stage_pin']==parent.pin(b'')
    parsed['graph_intervals']=intervals;parsed['census_stage_intervals']=census_stages
    indices=[STAGES.index(row[1]) for row in parsed['stages']]
    require(indices==sorted(set(indices)),'stage order or duplication differs')
    return parsed

PROBE_KEYS={'permission_observation'}|set(['F_launch_admitted', 'actual_F', 'authority', 'boundary_phase', 'boundary_report', 'case', 'close_calls', 'construction_result', 'consumer_state', 'dll_directory_close_returned', 'early_audit_blocked', 'external_expected_truth_verified', 'failure_phase', 'formal_result', 'full_P1_content_verified', 'full_runtime_binding_verified', 'graph_calls', 'guard', 'import_profile', 'independent_root_verified', 'inputs_phase', 'kernel_identity', 'live_at_report', 'namespace_alias_absent', 'namespace_phase', 'namespace_terminal', 'native_authorized', 'native_behavior_verified', 'old_inputs_successor_matches', 'old_namespace_successor_matches', 'parent_independently_authenticated_python_object_graph', 'permit_issued', 'post_metrics', 'primary', 'production_seal', 'resource_admission', 'resource_phase', 'retained_modules', 'role_bootstrap', 'run_authority', 'runtime_is_resource_owner', 'runtime_phase', 'runtime_phase_before_close', 'runtime_was_live', 'schema', 'scientific_evidence_adopted', 'secondary', 'self_handles_closed', 'source_bookends', 'source_epoch', 'source_phase', 'startup_profile', 'startup_tcb_authenticated', 'status', 'upstream_owner_verified'])|{'bootstrap_actor','producer_result'}


def parse_stderr(raw):
    return parse(SimpleNamespace(canonical=canonical,pin=pin,parse_diagnostic_stderr=parse_diagnostic_stderr),raw)


def record_shape(record,source_epoch):
    require(type(record) is dict and set(record)==PROBE_KEYS,'closed complete bootstrap probe fields required')
    require(record['schema']=='staged_saved_F_complete_bootstrap_probe_v1'
        and record['authority']=='DRAFT_NONAUTHORITATIVE' and record['case'] in ('discovery','import_discovery','producer')
        and record['source_epoch']==source_epoch,'complete bootstrap schema/case/source differs')
    require(record['status'] in ('completed','discovery_only','failed')
        and type(record['secondary']) is list and len(record['secondary'])<=8,'closed bootstrap status/errors required')
    validate_exception_images([record['primary'],*record['secondary']])
    require(all(record[key] is False for key in FLAGS) and record['live_at_report'] is False,'bootstrap authority differs')
    for key in ('dll_directory_close_returned','runtime_is_resource_owner','old_inputs_successor_matches',
            'old_namespace_successor_matches','runtime_was_live','namespace_alias_absent'):
        require(type(record[key]) is bool,'exact bootstrap boolean required: '+key)
    for key in ('runtime_phase_before_close','runtime_phase','resource_phase','inputs_phase','namespace_phase','source_phase',
            'boundary_phase','consumer_state','failure_phase'):
        require(record[key] is None or type(record[key]) is str and 0<len(record[key])<=80,'bounded bootstrap phase required')
    require(record['self_handles_closed'] is None or type(record['self_handles_closed']) is bool,'exact self-close boolean required')
    if record['close_calls'] is not None:
        require(type(record['close_calls']) is list and len(record['close_calls'])==2
            and all(uint(n,1) for n in record['close_calls']),'exact two close counters required')
    require(uint(record['source_bookends'],1024) and uint(record['retained_modules'],4096),'bounded source/retention observations required')
    require(record['graph_calls'] is None or uint(record['graph_calls'],GRAPH_CALL_CAP),'bounded graph stop counter required')
    require(record['early_audit_blocked'] is None or type(record['early_audit_blocked']) is list
        and len(record['early_audit_blocked'])<=8 and all(type(v) is str and len(v)<=160 for v in record['early_audit_blocked']),
        'bounded early audit failures required')
    if record['namespace_terminal'] is not None:namespace_shape(record['namespace_terminal'])
    if record['guard'] is not None:
        guard=record['guard'];require(type(guard) is dict and set(guard)==GUARD_KEYS,'closed input guard required')
        require(all(uint(guard[key],16384) for key in GUARD_KEYS-{'events','faults'}),'bounded guard counters required')
        require(type(guard['events']) is list and len(guard['events'])<=64
            and all(type(v) is str and len(v)<=160 for v in guard['events']),'bounded guard events required')
        require(type(guard['faults']) is list and len(guard['faults'])<=8,'bounded guard faults required')
    if record['boundary_report'] is not None:
        br=record['boundary_report'];require(type(br) is dict and set(br)==BOUNDARY_KEYS
            and br['schema']=='staged_saved_F_successor_import_boundary_report_v1'
            and br['authority']=='DRAFT_NONAUTHORITATIVE','closed import boundary observation required')
    return record


def decode(stdout,source_epoch):
    require(type(stdout) is bytes and len(stdout)<=STDOUT_CAP,'bounded complete child stdout required')
    value=unique_json(stdout)
    require(canonical(value)+b'\n'==stdout,'single complete canonical child line required')
    return record_shape(value,source_epoch)


def quiet_shape(value,plan_raw,code,argv,stdout,stderr):
    flags=('parent_independent_P1_verified','external_permission_verified','resource_admission','formal_result','run_authority','actual_F')
    keys={'schema','authority','kernel_identity','argv_pin','plan_pin','transport_pin','stdout_pin','stderr_pin','release_pin',
        'release_sent','writer_errors','child_success','transport_success','drain_observation','drain_observation_pin','quiet',*flags}
    require(type(value) is dict and set(value)==keys and value['schema']=='staged_saved_F_retained_parent_quiet_v1'
        and value['authority']=='DRAFT_NONAUTHORITATIVE' and all(value[key] is False for key in flags),'closed retained quiet receipt required')
    require(value['plan_pin']==pin(plan_raw) and value['transport_pin']==pin(code) and value['argv_pin']==pin(canonical(argv))
        and value['stdout_pin']==pin(stdout) and value['stderr_pin']==pin(stderr),'same retained manifest/transport/argv/streams required')
    require(type(argv) is list and len(argv)==10 and argv[-1]==pin(plan_raw)['sha256']
        and argv[6]==code.decode('utf8'),'manifest and transport must match actual command')
    frame=b'SAVED_PRE_ENTRY_V1:'+pin(plan_raw)['sha256'].encode('ascii')+b'\n'
    require(value['release_pin']==pin(frame) and value['release_sent'] is True and value['writer_errors']==[]
        and value['child_success'] is True and value['transport_success'] is True,'clean release and successful child required')
    quiet=value['quiet'];keys={'child_exit','process_handle_closed','pipes_closed','reader_threads_terminal','writer_thread_terminal',
        'killed','stdout_truncated','stderr_truncated','reader_errors','cleanup'}
    require(type(quiet) is dict and set(quiet)==keys and type(quiet['child_exit']) is int and quiet['child_exit']==0
        and all(quiet[key] is True for key in ('process_handle_closed','pipes_closed','reader_threads_terminal','writer_thread_terminal'))
        and all(quiet[key] is False for key in ('killed','stdout_truncated','stderr_truncated'))
        and quiet['reader_errors']==quiet['cleanup']==[],'successful retained terminal facts required')
    drain=value['drain_observation']
    require(type(drain) is dict and pin(canonical(drain))==value['drain_observation_pin']
        and drain['direct_child_pid']==value['kernel_identity']['pid']
        and all(drain[key] is True for key in ('pipes_closed','reader_threads_terminal'))
        and all(drain[key] is False for key in ('killed','stdout_truncated','stderr_truncated'))
        and drain['reader_errors']==drain['cleanup']==[],'same original terminal drain required')
    return value


def actor_shape(value,case,record):
    require(type(value) is dict and set(value)=={'schema','authority','phase','mode','terminal','permission','secondary_count',*ACTOR_FALSE}
        and value['schema']=='staged_saved_F_bootstrap_actor_observation_v1' and value['authority']=='DRAFT_NONAUTHORITATIVE'
        and value['phase']=='CLOSED' and value['mode']==case and type(value['secondary_count']) is int
        and value['secondary_count']==0 and all(value[key] is False for key in ACTOR_FALSE),'closed exact creating bootstrap actor required')
    terminal=value['terminal']
    require(type(terminal) is dict and set(terminal)=={'runtime_phase','resource_phase','consumer_state','close_calls','pending',
        'namespace_phase','cleanup_started'},'closed bootstrap terminal required')
    for key in ('runtime_phase','resource_phase','consumer_state','close_calls','namespace_phase'):
        require(terminal[key]==record[key],'actor/probe terminal differs: '+key)
    ns=record['namespace_terminal']
    require(terminal['pending']==ns['pending']==[False,False] and all(type(v) is bool for v in terminal['pending'])
        and terminal['cleanup_started'] is ns['cleanup_started'] is True,'same original namespace cleanup terminal required')
    require(value['permission']==record['permission_observation'],'actor/probe permission differs')
    return value


def common_success(parent,record,parsed,plan,code):
    require(record['primary'] is None and record['secondary']==[] and record['failure_phase'] is None
        and record['dll_directory_close_returned'] is True and record['early_audit_blocked']==[]
        and record['namespace_alias_absent'] is True,'clean complete bootstrap close required')
    case=plan['case']
    if case=='discovery':
        require(record['status']=='discovery_only' and record['startup_profile'] is not None,'startup discovery report required')
        for key in ('runtime_phase_before_close','runtime_phase','resource_phase','inputs_phase','namespace_phase','source_phase',
                'kernel_identity','close_calls','self_handles_closed','boundary_phase','boundary_report','post_metrics','graph_calls',
                'construction_result','namespace_terminal','permission_observation','bootstrap_actor','producer_result','consumer_state','guard','import_profile'):
            require(record[key] is None,'startup discovery opened state: '+key)
        require(record['source_bookends']==record['retained_modules']==0 and record['runtime_was_live'] is False
            and all(record[key] is False for key in ('runtime_is_resource_owner','old_inputs_successor_matches','old_namespace_successor_matches')),
            'startup discovery cannot own a project successor')
        require(not parsed['stages'] and not parsed['graph_frames'] and not parsed['census_frames']
            and parsed['non_stage_pin']==pin(b''),'startup discovery stderr must be empty')
        startup_shape(parent,record['startup_profile'],plan,code)
        return record['startup_profile']
    require(record['status']=='completed' and record['runtime_phase']==record['resource_phase']=='CLOSED'
        and record['source_phase']==record['inputs_phase']==record['namespace_phase']=='CONSUMED'
        and record['close_calls']==[1,1] and all(type(v) is int for v in record['close_calls'])
        and all(record[key] is True for key in ('runtime_is_resource_owner','old_inputs_successor_matches',
            'old_namespace_successor_matches','self_handles_closed')),'same closed project successor and self HANDLEs required')
    require(record['runtime_phase_before_close']==('LIVE' if case=='producer' else 'OBSERVED')
        and record['runtime_was_live'] is (case=='producer') and record['consumer_state']==('CONSUMED' if case=='producer' else None),
        'closed case-specific LIVE/consumer sequence required')
    require(record['startup_profile'] is None and record['import_profile'] is not None and record['retained_modules']>0,
        'closed import observation and retained module count required')
    profile=profile_data(record['import_profile'])
    wanted={name[:-3].replace('/','.').removesuffix('.__init__'):str(parent.ROOT/name)
        for name in plan['source_pins'] if name.startswith('src/') and name.endswith('.py')
            or name=='experiments/staged_rts24_saved_fresh_adoption_v1.py'}
    observed={row[0]:row[2] for row in profile['modules'] if len(row)==5 and type(row[2]) is str
        and Path(row[2]).is_relative_to(parent.ROOT)}
    require(len(wanted)==37 and observed==wanted,'complete selected project import metadata required')
    namespace_shape(record['namespace_terminal'],success=True);actor_shape(record['bootstrap_actor'],case,record)
    guard=record['guard']
    require(guard is not None and guard['sentinel']==1 and guard['source_open_attempts']>0 and guard['faults']==[]
        and all(guard[key]==0 for key in ('protected_open_attempts','write_attempts','process_attempts')),'clean input guard required')
    events=guard['events']
    require(events.index('self_handles_live')<events.index('source_read_begin')<events.index('transfer_committed')
        <events.index('self_handles_closed'),'self/source/transfer/close event order differs')
    br=record['boundary_report']
    require(br is not None and record['boundary_phase']==br['phase']=='CLOSED' and br['fault_kind']==''
        and br['hook_active'] is False and br['machinery_observed_stage']==br['machinery_authenticated_stage']==2
        and br['machinery_authentication_pending'] is False and br['violations']==0,'closed complete import boundary required')
    yes=('callback_retained','hook_installation_observed','finder_function_mutation_guard_installed',
        'finder_function_metadata_bookend_verified','forced_numpy_SVE_false','source49_bookend_equal','import_boundary_completed')
    counts=('optional_Popen_attempts','blocked_optional_attempts','installation_sentinel_observed','audit_handoff_observed')
    for key in yes:require(br[key] is True,'import boundary success flag differs: '+key)
    for key in counts:require(type(br[key]) is int and br[key]==1,'import boundary counter differs: '+key)
    require(uint(br['internal_introspection_events'],4096),'bounded import introspection count required')
    for key in BOUNDARY_KEYS-set(yes)-set(counts)-{'schema','authority','phase','fault_kind','hook_active','machinery_observed_stage',
            'machinery_authenticated_stage','machinery_authentication_pending','violations','internal_introspection_events'}:
        require(br[key] is False,'import boundary authority differs: '+key)
    metrics=record['post_metrics']
    require(type(metrics) is dict and set(metrics)=={'returned','idle_getter_events','busy_getter_events',*METRICS}
        and metrics['returned'] is True,'closed post-import metrics required')
    for key in METRICS:
        row=metrics[key];require(type(row) is list and len(row)==3 and uint(row[0],4096) and row[0]>0
            and all(type(v) is float and math.isfinite(v) and v>=0 for v in row[1:]) and row[2]<=row[1],'bounded metric required')
    require(uint(metrics['idle_getter_events'],1000000) and metrics['idle_getter_events']>0
        and uint(metrics['busy_getter_events'],1000000),'bounded getter metrics required')
    require(parsed['graph_complete'] and parsed['stage_parse_complete'] and not parsed['stack_present']
        and [row[1] for row in parsed['stages']]==list(STAGES),'complete stage/graph trace required')
    exits=[row for row in parsed['graph_frames'] if row[3]=='exit']
    require(all(row[5] is not None for row in exits) and 0<len(exits)==record['graph_calls']<=GRAPH_CALL_CAP
        and len(parsed['graph_frames'])==2*len(exits),'complete observed graph pairs required')
    require(parsed['census_stage_intervals']==['before_adapter_import','adapter_import_returned']
        and parsed['census_frames'],'bounded import census required')
    first,last=parsed['census_frames'][0],parsed['census_frames'][-1]
    require(last['reason']=='import_return_before2048' and last['active'] is False and last['inflight'] is False
        and last['passed']==last['entered']==last['observed'] and last['rejected']==last['diagnostic_error_count']==0
        and last['machinery_stage']==2,'complete successful import census terminal required')
    require(parsed['stages'][1][2]<=first['start_clock']<=last['snapshot_clock']<=parsed['stages'][3][2],
        'census import clock window differs')
    return profile


def exact_graph(case,record,parsed):
    contract=dict(_EXACT_CONTRACTS)[case]
    if contract is None:return False
    if case=='discovery':return True
    require(type(contract) is dict and set(contract)=={'calls','intervals','metrics','source_bookends'}
        and type(contract['calls']) is int and 0<contract['calls']<=GRAPH_CALL_CAP,'fixed exact graph contract required')
    require(record['graph_calls']==contract['calls'] and parsed['graph_intervals']==contract['intervals']
        and {key:record['post_metrics'][key][0] for key in METRICS}==contract['metrics']
        and record['source_bookends']==contract['source_bookends'],'exact complete graph DAG/counters differ')
    return True


def replay(parent,plan_raw,code,argv,stdout,stderr,quiet,profile_dependency=None):
    """Internal data checks; the source-held parent obtains quiet from its exact actor."""
    plan=unique_json(plan_raw)
    require(canonical(plan)==plan_raw and plan['bootstrap_pin']==pin(code),'same canonical bootstrap manifest required')
    require(plan['case'] in dict(_EXACT_CONTRACTS) and plan['source_epoch']==parent.SOURCE_SHA
        and pin(canonical(plan['source_pins']))['sha256']==parent.SOURCE_SHA,'same fixed source epoch required')
    quiet_shape(quiet,plan_raw,code,argv,stdout,stderr)
    guard=parent.validate_memory_guard(quiet['drain_observation']['memory_guard'])
    require(guard['binding']['parent_pid']==parent.controller_pid
        and guard['binding']['child_pid']==quiet['kernel_identity']['pid'],'same live sampled parent/child pair required')
    record=decode(stdout,parent.SOURCE_SHA);require(record['case']==plan['case'],'held manifest/child case differs')
    parsed=parse_stderr(stderr);profile=common_success(parent,record,parsed,plan,code)
    if plan['case']!='discovery':kernel_match(parent,record,quiet['kernel_identity'],argv)
    producer=None
    if plan['case']=='producer':
        require(record['construction_result'] is None and type(record['producer_result']) is dict,'unique complete producer result required')
        result=record['producer_result'];actor=record['bootstrap_actor']
        require(result['terminal']==actor['terminal'] and result['permission']==actor['permission']==record['permission_observation'],
            'same actor/producer/probe terminal and permission required')
        producer=parent.producer_data_replay(canonical(result),quiet['quiet'],plan['source_pins'])
        profile_relation(parent,plan_raw,code,profile_dependency,observed=canonical(profile),
            producer_identity=quiet['kernel_identity'])
    elif plan['case']=='import_discovery':
        require(record['producer_result'] is None,'import discovery cannot carry a producer result')
        construction_shape(record['construction_result']);permission_shape(record['permission_observation'],True)
    else:require(record['producer_result'] is None and record['bootstrap_actor'] is None,'startup discovery cannot create an actor')
    graph_closed=exact_graph(plan['case'],record,parsed)
    return dict(schema='staged_saved_F_complete_parent_data_replay_v1',authority='DRAFT_NONAUTHORITATIVE',
        accepted=graph_closed,data_relationships_replayed=True,exact_graph_contract_verified=graph_closed,
        remaining_gate=None if graph_closed else 'exact_complete_graph_contract_unresolved',
        case=plan['case'],child_record_pin=pin(stdout[:-1]),profile_pin=pin(canonical(profile)),producer_replay=producer,
        graph_counts=parsed['graph_counts'],source_bookends=record['source_bookends'],
        physical_parent_P1_reads=0,parent_independent_P1_verified=False,parent_python_graph_attested=False,
        external_permission_verified=False,scientific_evidence_adopted=False,resource_admission=False,
        formal_result=False,run_authority=False,actual_F=False)


def profile_relation(parent,producer_plan_raw,code,dependency,observed=None,producer_identity=None):
    """Reopen an earlier independent accepted import-discovery receipt, never the current output."""
    require(type(dependency) is dict and set(dependency)=={'profile_raw','receipt_raw','manifest_raw','admission_raw','registration_raw'},
        'complete independent profile dependency required')
    require(all(type(raw) is bytes and len(raw)<=1048576 for raw in dependency.values()),'bounded raw profile dependency required')
    plan=unique_json(producer_plan_raw);reference=unique_json(dependency['manifest_raw'])
    receipt=open_saved_receipt(dependency['receipt_raw']);admission=unique_json(dependency['admission_raw']);registration=unique_json(dependency['registration_raw'])
    require(all(canonical(value)==dependency[key] for value,key in ((reference,'manifest_raw'),(admission,'admission_raw'),(registration,'registration_raw'))),'canonical independent profile artifacts required')
    require(reference['case']=='import_discovery' and plan['case']=='producer' and reference['nonce']!=plan['nonce'],
        'earlier independent import-discovery manifest required')
    for key in ('source_pins','source_epoch','bootstrap_pin','executable_pin','python','environment','cwd','initial_paths',
            'selected_runtime_file_observations','startup_absent','startup_profile','namespace_helper','import_helper','import_policy',
            'producer_helpers','graph_contract'):
        require(reference[key]==plan[key],'independent profile scope differs: '+key)
    require(reference['import_profile'] is None and plan['import_profile']['pin']==pin(dependency['profile_raw'])
        and plan['import_profile']['path']==str(parent.OUT/'import_profile.json'),'same pre-existing import profile required')
    require(receipt['accepted'] is True and receipt['case']=='import_discovery'
        and receipt['manifest_raw_base64']==base64.b64encode(dependency['manifest_raw']).decode('ascii'),
        'accepted earlier import-discovery receipt required')
    saved=audit_saved(parent,dependency['receipt_raw'],code,profile_dependency=None)
    require(saved['accepted'] is True and saved['profile_pin']==pin(dependency['profile_raw']),'independent accepted profile replay required')
    record=decode(base64.b64decode(receipt['stdout_raw_base64'],validate=True),parent.SOURCE_SHA)
    require(canonical(profile_data(record['import_profile']))==dependency['profile_raw'],'published profile differs from earlier child bytes')
    if observed is not None:require(observed==dependency['profile_raw'],'current import profile differs from independent reference')
    if producer_identity is not None:
        identity=receipt['quiet_receipt']['kernel_identity']
        require((identity['pid'],identity['creation'])!=(producer_identity['pid'],producer_identity['creation'])
            and identity['creation']<producer_identity['creation'],'profile must precede this distinct producer process')
    flags=('external_permission_verified','parent_independent_P1_verified','resource_admission','formal_result','run_authority','actual_F')
    keys={'schema','authority','accepted','receipt_pin','profile_pin','manifest_pin','registration_pin','transport_pin',
        'environment_pin','source_pins_pin','helper_pins_pin',*flags}
    require(type(admission) is dict and set(admission)==keys and admission['schema']=='staged_saved_F_independent_import_profile_admission_v1'
        and admission['authority']=='DRAFT_NONAUTHORITATIVE' and admission['accepted'] is True
        and all(admission[key] is False for key in flags),'closed independent data profile admission required')
    expected=dict(receipt_pin=pin(dependency['receipt_raw']),profile_pin=pin(dependency['profile_raw']),
        manifest_pin=pin(dependency['manifest_raw']),registration_pin=pin(dependency['registration_raw']),transport_pin=pin(code),
        environment_pin=pin(canonical(plan['environment'])),source_pins_pin=pin(canonical(plan['source_pins'])),
        helper_pins_pin=pin(canonical(plan['producer_helpers'])))
    require(all(admission[key]==value for key,value in expected.items()),'independent admission dependency pin differs')
    require(type(registration) is dict and set(registration)=={'schema','authority','accepted','transport_pin','source_pins_pin','helper_pins_pin',*flags}
        and registration['schema']=='staged_saved_F_complete_parent_registration_v1' and registration['authority']=='DRAFT_NONAUTHORITATIVE'
        and registration['accepted'] is True and all(registration[key] is False for key in flags)
        and all(registration[key]==expected[key] for key in ('transport_pin','source_pins_pin','helper_pins_pin')),
        'same independent registration data context required')
    require(_PROFILE_ACCEPTED_ANCHOR is not None and _PROFILE_ACCEPTED_ANCHOR==(expected['registration_pin']['sha256'],),
        'external accepted profile registration anchor remains open')
    return dict(profile_pin=expected['profile_pin'],receipt_pin=expected['receipt_pin'],admission_pin=pin(dependency['admission_raw']),
        registration_pin=expected['registration_pin'],external_permission_verified=False,parent_independent_P1_verified=False,
        resource_admission=False,formal_result=False,run_authority=False,actual_F=False)


def audit_saved(parent,raw,code,profile_dependency=None):
    """Saved-byte replay is evidence checking; it never reconstructs a live actor or authority."""
    require(type(raw) is bytes and len(raw)<=1048576,'bounded canonical saved parent receipt required')
    row=open_saved_receipt(raw)
    flags=('external_permission_verified','parent_independent_P1_verified','resource_admission','formal_result','run_authority','actual_F')
    keys={'schema','authority','case','accepted','manifest_raw_base64','argv','stdout_raw_base64','stderr_raw_base64','quiet_receipt',
        'result','primary','secondary','context_before','context_after','parent_controller_pid',*flags}
    require(type(row) is dict and set(row)==keys and row['schema']=='staged_saved_F_complete_parent_receipt_v1'
        and row['authority']=='DRAFT_NONAUTHORITATIVE' and row['accepted'] is True and row['primary'] is None
        and row['secondary']==[] and all(row[key] is False for key in flags),'accepted saved parent data receipt required')
    require(type(row['parent_controller_pid']) is int and row['parent_controller_pid']>0,'creating parent pid required')
    manifest=base64.b64decode(row['manifest_raw_base64'],validate=True)
    stdout=base64.b64decode(row['stdout_raw_base64'],validate=True);stderr=base64.b64decode(row['stderr_raw_base64'],validate=True)
    require(row['case']==unique_json(manifest)['case'],'saved parent case differs')
    drain=row['quiet_receipt']['drain_observation']
    guard=parent.validate_memory_guard(drain['memory_guard'])
    require(guard['binding']['parent_pid']==row['parent_controller_pid']
        and guard['binding']['child_pid']==row['quiet_receipt']['kernel_identity']['pid'],'saved memory/process pair differs')
    context=parent.input_context(manifest,code,row['argv'],profile_dependency=profile_dependency)
    require(row['context_before']==row['context_after']==context,'saved parent input bookends differ')
    saved_parent=SimpleNamespace(**vars(parent));saved_parent.controller_pid=row['parent_controller_pid']
    result=replay(saved_parent,manifest,code,row['argv'],stdout,stderr,row['quiet_receipt'],profile_dependency=profile_dependency)
    require(result==row['result'] and result['accepted'] is True,'saved complete replay differs or exact graph remains open')
    return result


def current():
    return None,dict(schema='staged_saved_F_complete_bootstrap_validation_contract_v1',authority='DRAFT_NONAUTHORITATIVE',
        stdout_cap=STDOUT_CAP,stderr_cap=STDERR_CAP,graph_stop=GRAPH_CALL_CAP,exact_import_graph_contract=None,
        exact_producer_graph_contract=None,raw_streams_bound_to_retained_actor=True,
        independent_profile_requires_earlier_accepted_receipt=True,physical_parent_P1_reads=0,
        external_permission_verified=False,parent_independent_P1_verified=False,resource_admission=False,
        formal_result=False,run_authority=False,actual_F=False)



def open_saved_receipt(raw):
    value=unique_json(raw)
    flags=('external_permission_verified','parent_independent_P1_verified','resource_admission','formal_result','run_authority','actual_F')
    require(canonical(value)==raw and type(value) is dict
        and set(value)=={'schema','authority','accepted','receipt','receipt_pin','retirement','retirement_evidence_base64','terminal_parent_phase',*flags}
        and value['schema']=='staged_saved_F_complete_parent_terminal_v1' and value['authority']=='DRAFT_NONAUTHORITATIVE'
        and value['accepted'] is True and value['terminal_parent_phase']=='RETIRED' and all(value[key] is False for key in flags),
        'accepted complete parent and exact actor retirement required')
    row=value['receipt'];row_raw=canonical(row)
    require(value['receipt_pin']==pin(row_raw) and row['accepted'] is True,'same accepted parent result bytes required')
    evidence_raw=base64.b64decode(value['retirement_evidence_base64'],validate=True);evidence=unique_json(evidence_raw)
    require(canonical(evidence)==evidence_raw and type(evidence) is dict
        and set(evidence)=={'schema','authority','quiet_snapshot_pin','parent_result_pin','accepted',*flags}
        and evidence['schema']=='staged_saved_F_parent_retirement_record_v1' and evidence['authority']=='DRAFT_NONAUTHORITATIVE'
        and evidence['accepted'] is True and all(evidence[key] is False for key in flags)
        and evidence['parent_result_pin']==pin(row_raw) and evidence['quiet_snapshot_pin']==pin(canonical(row['quiet_receipt'])),
        'same retained terminal snapshot and result retirement required')
    retired=value['retirement']
    require(type(retired) is dict and set(retired)=={'schema','authority','exact_registry_row_retired','terminal_snapshot_pin','evidence_pin',*flags}
        and retired['schema']=='staged_saved_F_parent_actor_retirement_v1' and retired['authority']=='DRAFT_NONAUTHORITATIVE'
        and retired['exact_registry_row_retired'] is True and all(retired[key] is False for key in flags)
        and retired['terminal_snapshot_pin']==evidence['quiet_snapshot_pin'] and retired['evidence_pin']==pin(evidence_raw),
        'exact actor retirement data differs')
    return row


def startup_relation(parent,producer_plan_raw,code,dependency,observed=None,producer_identity=None):
    """Reopen an earlier independent accepted startup-discovery receipt, never the current output."""
    require(type(dependency) is dict and set(dependency)=={'profile_raw','receipt_raw','manifest_raw','admission_raw','registration_raw'},
        'complete independent profile dependency required')
    require(all(type(raw) is bytes and len(raw)<=1048576 for raw in dependency.values()),'bounded raw profile dependency required')
    plan=unique_json(producer_plan_raw);reference=unique_json(dependency['manifest_raw'])
    receipt=open_saved_receipt(dependency['receipt_raw']);admission=unique_json(dependency['admission_raw']);registration=unique_json(dependency['registration_raw'])
    require(all(canonical(value)==dependency[key] for value,key in ((reference,'manifest_raw'),(admission,'admission_raw'),(registration,'registration_raw'))),'canonical independent profile artifacts required')
    require(reference['case']=='discovery' and plan['case'] in ('import_discovery','producer') and reference['nonce']!=plan['nonce'],
        'earlier independent startup-discovery manifest required')
    for key in ('source_pins','source_epoch','bootstrap_pin','executable_pin','python','environment','cwd','initial_paths',
            'selected_runtime_file_observations','startup_absent','namespace_helper','import_helper','import_policy',
            'producer_helpers','graph_contract'):
        require(reference[key]==plan[key],'independent profile scope differs: '+key)
    require(reference['startup_profile'] is None and plan['startup_profile']['pin']==pin(dependency['profile_raw'])
        and plan['startup_profile']['path']==str(parent.OUT/'startup_profile.json'),'same pre-existing import profile required')
    require(receipt['accepted'] is True and receipt['case']=='discovery'
        and receipt['manifest_raw_base64']==base64.b64encode(dependency['manifest_raw']).decode('ascii'),
        'accepted earlier import-discovery receipt required')
    saved=audit_saved(parent,dependency['receipt_raw'],code,profile_dependency=None)
    require(saved['accepted'] is True and saved['profile_pin']==pin(dependency['profile_raw']),'independent accepted profile replay required')
    record=decode(base64.b64decode(receipt['stdout_raw_base64'],validate=True),parent.SOURCE_SHA)
    require(canonical(record['startup_profile'])==dependency['profile_raw'],'published profile differs from earlier child bytes')
    if observed is not None:require(observed==dependency['profile_raw'],'current import profile differs from independent reference')
    if producer_identity is not None:
        identity=receipt['quiet_receipt']['kernel_identity']
        require((identity['pid'],identity['creation'])!=(producer_identity['pid'],producer_identity['creation'])
            and identity['creation']<producer_identity['creation'],'profile must precede this distinct producer process')
    flags=('external_permission_verified','parent_independent_P1_verified','resource_admission','formal_result','run_authority','actual_F')
    keys={'schema','authority','accepted','receipt_pin','profile_pin','manifest_pin','registration_pin','transport_pin',
        'environment_pin','source_pins_pin','helper_pins_pin',*flags}
    require(type(admission) is dict and set(admission)==keys and admission['schema']=='staged_saved_F_independent_startup_profile_admission_v1'
        and admission['authority']=='DRAFT_NONAUTHORITATIVE' and admission['accepted'] is True
        and all(admission[key] is False for key in flags),'closed independent data profile admission required')
    expected=dict(receipt_pin=pin(dependency['receipt_raw']),profile_pin=pin(dependency['profile_raw']),
        manifest_pin=pin(dependency['manifest_raw']),registration_pin=pin(dependency['registration_raw']),transport_pin=pin(code),
        environment_pin=pin(canonical(plan['environment'])),source_pins_pin=pin(canonical(plan['source_pins'])),
        helper_pins_pin=pin(canonical(plan['producer_helpers'])))
    require(all(admission[key]==value for key,value in expected.items()),'independent admission dependency pin differs')
    require(type(registration) is dict and set(registration)=={'schema','authority','accepted','transport_pin','source_pins_pin','helper_pins_pin',*flags}
        and registration['schema']=='staged_saved_F_complete_parent_registration_v1' and registration['authority']=='DRAFT_NONAUTHORITATIVE'
        and registration['accepted'] is True and all(registration[key] is False for key in flags)
        and all(registration[key]==expected[key] for key in ('transport_pin','source_pins_pin','helper_pins_pin')),
        'same independent registration data context required')
    require(_PROFILE_ACCEPTED_ANCHOR is not None and _PROFILE_ACCEPTED_ANCHOR==(expected['registration_pin']['sha256'],),
        'external accepted profile registration anchor remains open')
    return dict(profile_pin=expected['profile_pin'],receipt_pin=expected['receipt_pin'],admission_pin=pin(dependency['admission_raw']),
        registration_pin=expected['registration_pin'],external_permission_verified=False,parent_independent_P1_verified=False,
        resource_admission=False,formal_result=False,run_authority=False,actual_F=False)


def replay_retained(parent,actor,plan_raw,code,argv,stdout,stderr,profile_dependency=None):
    """Only the creating source-held parent supplies these original facts."""
    require(type(actor) is parent.quiet_actor_type and actor._creator==(os.getpid(),get_ident())
        and parent.quiet_actor_registry.get(id(actor)) is actor,'exact creating retained child actor required')
    quiet=parent.quiet_finish(actor)
    return replay(parent,plan_raw,code,argv,stdout,stderr,quiet,profile_dependency=profile_dependency)


def reopen_failure_terminal(raw):
    """Reopen the fixed rejected format; this never accepts a complete F."""
    require(type(raw) is bytes and len(raw)<=1048576,'bounded saved failed parent required')
    value=unique_json(raw);require(type(value) is dict and canonical(value)==raw,'canonical failed parent required')
    if value.get('schema')=='staged_saved_F_parent_emergency_failure_v1':return reopen_emergency_failure(raw)
    flags=('external_permission_verified','parent_independent_P1_verified','resource_admission','formal_result','run_authority','actual_F')
    keys={'schema','authority','accepted','failure','failure_pin','retirement','retirement_evidence_base64','retirement_errors','terminal_parent_phase',*flags}
    require(type(value) is dict and set(value)==keys and value['schema']=='staged_saved_F_complete_parent_failure_v1'
        and value['authority']=='DRAFT_NONAUTHORITATIVE' and value['accepted'] is False
        and all(value[key] is False for key in flags) and value['terminal_parent_phase'] in ('RETIRED','UNRESOLVED'),
        'closed rejected parent terminal required')
    core=value['failure'];keys={'schema','authority','accepted','stage','primary','secondary','manifest_raw_base64','transport_pin','argv_pin',
        'stdout_raw_base64','stderr_raw_base64','stdout_pin','stderr_pin','quiet_snapshot','prior_retirement_parent_result_pin',*flags}
    require(type(core) is dict and set(core)==keys and core['schema']=='staged_saved_F_complete_parent_failure_core_v1'
        and core['authority']=='DRAFT_NONAUTHORITATIVE' and core['accepted'] is False and all(core[key] is False for key in flags)
        and pin(canonical(core))==value['failure_pin'],'same closed rejected result bytes required')
    require(type(core['stage']) is str and core['stage'] in ('CAPTURE','PARENT_TERMINAL')
        and type(core['secondary']) is list and len(core['secondary'])<=16
        and type(value['retirement_errors']) is list and len(value['retirement_errors'])<=4,'bounded rejected stages/errors required')
    for image in [core['primary'],*core['secondary'],*value['retirement_errors']]:validate_exception_images([image])
    require(core['primary'] is not None,'original rejected parent primary required')
    stdout=base64.b64decode(core['stdout_raw_base64'],validate=True);stderr=base64.b64decode(core['stderr_raw_base64'],validate=True)
    require(len(stdout)<=STDOUT_CAP and len(stderr)<=STDERR_CAP and pin(stdout)==core['stdout_pin'] and pin(stderr)==core['stderr_pin'],
        'same original failed child streams required')
    require(len(base64.b64decode(core['manifest_raw_base64'],validate=True))<=131072,'bounded failed manifest bytes required')
    checked_pin(core['transport_pin'],131072);checked_pin(core['argv_pin'],1048576)
    failure_retirement_shape(value,core)
    retired=value['retirement']
    if retired is not None:
        evidence_raw=base64.b64decode(value['retirement_evidence_base64'],validate=True);evidence=unique_json(evidence_raw)
        require(type(evidence) is dict and set(evidence)=={'schema','authority','quiet_snapshot_pin','parent_result_pin','accepted',*flags}
            and evidence['schema']=='staged_saved_F_parent_retirement_record_v1' and evidence['authority']=='DRAFT_NONAUTHORITATIVE'
            and type(evidence['accepted']) is bool and all(evidence[key] is False for key in flags)
            and (evidence['accepted'] is False or core['prior_retirement_parent_result_pin'] is not None)
            and canonical(evidence)==evidence_raw and evidence['quiet_snapshot_pin']==pin(canonical(core['quiet_snapshot']))
            and evidence['parent_result_pin']==(value['failure_pin'] if core['prior_retirement_parent_result_pin'] is None
                else core['prior_retirement_parent_result_pin']),'same failure or prior retirement result pin required')
        require(type(retired) is dict and set(retired)=={'schema','authority','exact_registry_row_retired','terminal_snapshot_pin','evidence_pin',*flags}
            and retired['schema']=='staged_saved_F_parent_actor_retirement_v1' and retired['authority']=='DRAFT_NONAUTHORITATIVE'
            and retired['exact_registry_row_retired'] is True and retired['terminal_snapshot_pin']==evidence['quiet_snapshot_pin']
            and retired['evidence_pin']==pin(evidence_raw) and all(retired[key] is False for key in flags),
            'same retired failed actor data required')
    else:require(value['retirement_evidence_base64'] is None or value['terminal_parent_phase']=='UNRESOLVED',
        'unresolved failed retirement must remain visible')
    if value['terminal_parent_phase']=='RETIRED':
        require(retired is not None or core['stage']=='CAPTURE' and core['quiet_snapshot'] is None
            and not core['secondary'] and not value['retirement_errors'],'retired rejection needs exact actor or clean pre-capture cleanup')
    elif retired is not None:require(value['retirement_errors'],'unresolved parent with retired quiet actor must preserve its failure')
    return dict(schema='staged_saved_F_rejected_parent_replay_v1',authority='DRAFT_NONAUTHORITATIVE',accepted=False,
        failure_pin=value['failure_pin'],terminal_parent_phase=value['terminal_parent_phase'],physical_parent_P1_reads=0,
        external_permission_verified=False,parent_independent_P1_verified=False,resource_admission=False,
        formal_result=False,run_authority=False,actual_F=False)


def reopen_emergency_failure(raw):
    value=unique_json(raw)
    flags=('external_permission_verified','parent_independent_P1_verified','resource_admission','formal_result','run_authority','actual_F')
    require(type(value) is dict and set(value)=={'schema','authority','accepted','stage','terminal_parent_phase','primary','secondary',
        'manifest_raw_base64','transport_pin','argv_pin',*flags} and canonical(value)==raw
        and value['schema']=='staged_saved_F_parent_emergency_failure_v1' and value['authority']=='DRAFT_NONAUTHORITATIVE'
        and value['accepted'] is False and value['terminal_parent_phase']=='UNRESOLVED'
        and value['stage'] in ('CAPTURE','PARENT_TERMINAL') and all(value[key] is False for key in flags),
        'closed unresolved emergency parent failure required')
    require(value['primary'] is not None and type(value['secondary']) is list and len(value['secondary'])<=8,
        'original emergency primary and bounded publication errors required')
    for image in [value['primary'],*value['secondary']]:validate_exception_images([image])
    require(len(base64.b64decode(value['manifest_raw_base64'],validate=True))<=131072,'bounded original emergency manifest required')
    checked_pin(value['transport_pin'],131072);checked_pin(value['argv_pin'],1048576)
    return dict(schema='staged_saved_F_rejected_parent_replay_v1',authority='DRAFT_NONAUTHORITATIVE',accepted=False,
        failure_pin=pin(raw),terminal_parent_phase='UNRESOLVED',physical_parent_P1_reads=0,
        external_permission_verified=False,parent_independent_P1_verified=False,resource_admission=False,
        formal_result=False,run_authority=False,actual_F=False)


def failure_retirement_shape(value,core):
    flags=('external_permission_verified','parent_independent_P1_verified','resource_admission','formal_result','run_authority','actual_F')
    prior=core['prior_retirement_parent_result_pin']
    if prior is not None:checked_pin(prior,1048576)
    encoded=value['retirement_evidence_base64'];retired=value['retirement']
    if encoded is None:
        require(retired is None and prior is None,'retirement or prior result requires exact held evidence')
        return
    require(type(encoded) is str and len(encoded)<=8192,'bounded failed retirement evidence required')
    raw=base64.b64decode(encoded,validate=True);evidence=unique_json(raw)
    require(type(evidence) is dict and set(evidence)=={'schema','authority','quiet_snapshot_pin','parent_result_pin','accepted',*flags}
        and canonical(evidence)==raw and evidence['schema']=='staged_saved_F_parent_retirement_record_v1'
        and evidence['authority']=='DRAFT_NONAUTHORITATIVE' and type(evidence['accepted']) is bool
        and all(evidence[key] is False for key in flags) and (evidence['accepted'] is False or prior is not None),
        'closed failed retirement evidence required even when unresolved')
    require(core['quiet_snapshot'] is not None and evidence['quiet_snapshot_pin']==pin(canonical(core['quiet_snapshot']))
        and evidence['parent_result_pin']==(value['failure_pin'] if prior is None else prior),'same unresolved terminal/result evidence required')
    checked_pin(evidence['quiet_snapshot_pin'],40960);checked_pin(evidence['parent_result_pin'],1048576)
    if retired is None:require(value['terminal_parent_phase']=='UNRESOLVED' and value['retirement_errors'],
        'missing actual registry retirement must preserve unresolved error')
