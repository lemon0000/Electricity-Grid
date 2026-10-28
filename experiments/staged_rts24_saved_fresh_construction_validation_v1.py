"""Bounded construction terminal data/replay; grants no runtime authority."""
import base64
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import zlib

if sys.flags.optimize!=0:raise RuntimeError('unoptimized terminal oracle required')

STAGES=('loader_ready','before_adapter_import','adapter_import_returned','after_adapter_import_attempt',
    'before_machinery_authentication','machinery_authenticated','before_source_bytes','after_source_bytes',
    'before_adapter_roots','after_adapter_roots','before_final_source_bookend','after_final_source_bookend',
    'before_retention','after_retention','before_boundary_close','after_boundary_close','before_profile','after_profile',
    'before_finish_import','after_finish_import','before_final_runtime_close','after_final_runtime_close')
GRAPH_CALL_CAP=43
GRAPH_IMAGE_CAP=4194304
INTERVALS={'<before_loader_ready>':['namespace']*19,'loader_ready':['namespace']*2,
    'after_adapter_import_attempt':['namespace']*5,'before_source_bytes':['namespace'],
    'before_adapter_roots':['adapter'],'before_boundary_close':['adapter']*2,'before_profile':['adapter'],
    'before_finish_import':['namespace','adapter','adapter','namespace','adapter','namespace','adapter'],
    'after_finish_import':['namespace','adapter'],'before_final_runtime_close':['namespace','adapter','namespace']}
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


RECEIPT_FIELDS=set(['accepted', 'authority', 'bounded_drain', 'cap_seconds', 'case', 'charged_seconds', 'child_exit', 'cleanup', 'context_after', 'context_before', 'drain_reason', 'expected_manifest_pin', 'memory_observation', 'memory_observation_source', 'parent_controller_pid', 'parent_kernel_identity', 'parent_process_handle_closed', 'plan_pin', 'primary', 'profile_publication', 'release_sent', 'result', 'schema', 'stderr_pin', 'stderr_raw_base64', 'stdin_closed', 'stdout_pin', 'stdout_raw_base64', 'transport_pin', 'writer_errors', 'writer_thread_terminal'])|set(FLAGS)

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

PROBE_KEYS=set(['F_launch_admitted', 'actual_F', 'authority', 'boundary_phase', 'boundary_report', 'case', 'close_calls', 'construction_result', 'consumer_state', 'dll_directory_close_returned', 'early_audit_blocked', 'external_expected_truth_verified', 'failure_phase', 'formal_result', 'full_P1_content_verified', 'full_runtime_binding_verified', 'graph_calls', 'guard', 'import_profile', 'independent_root_verified', 'inputs_phase', 'kernel_identity', 'live_at_report', 'namespace_alias_absent', 'namespace_phase', 'namespace_terminal', 'native_authorized', 'native_behavior_verified', 'old_inputs_successor_matches', 'old_namespace_successor_matches', 'parent_independently_authenticated_python_object_graph', 'permit_issued', 'post_metrics', 'primary', 'production_seal', 'resource_admission', 'resource_phase', 'retained_modules', 'role_bootstrap', 'run_authority', 'runtime_is_resource_owner', 'runtime_phase', 'runtime_phase_before_close', 'runtime_was_live', 'schema', 'scientific_evidence_adopted', 'secondary', 'self_handles_closed', 'source_bookends', 'source_epoch', 'source_phase', 'startup_profile', 'startup_tcb_authenticated', 'status', 'upstream_owner_verified'])

def parse(parent,raw):
    assert type(raw) is bytes and len(raw)<=32768
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


def record_shape(parent,record):
    require(type(record) is dict and set(record)==PROBE_KEYS,'closed construction probe fields required')
    require(record['schema']=='staged_saved_F_project_construction_probe_v2' and record['authority']=='DRAFT_NONAUTHORITATIVE',
        'construction probe schema differs')
    require(record['case'] in ('discovery','import_discovery',None) and record['source_epoch']==parent.SOURCE_SHA,'case/source epoch differs')
    require(record['status'] in ('completed','failed','discovery_only'),'closed probe status required')
    require(all(record[key] is False for key in FLAGS) and record['live_at_report'] is False,'probe authority differs')
    require(type(record['secondary']) is list and len(record['secondary'])<=8,'bounded cleanup errors required')
    parent.validate_exception_images([record['primary'],*record['secondary']])
    for key in ('runtime_was_live','runtime_is_resource_owner','old_inputs_successor_matches','old_namespace_successor_matches',
            'namespace_alias_absent','dll_directory_close_returned'):
        require(type(record[key]) is bool,'probe boolean type differs: '+key)
    require(record['consumer_state'] is None,'unadmitted construction cannot reserve a consumer')
    for key in ('runtime_phase_before_close','runtime_phase','resource_phase','inputs_phase','namespace_phase',
            'source_phase','boundary_phase','failure_phase'):
        require(record[key] is None or type(record[key]) is str and 0<len(record[key])<=80,'bounded phase required: '+key)
    require(record['self_handles_closed'] is None or type(record['self_handles_closed']) is bool,'handle terminal boolean required')
    if record['close_calls'] is not None:
        require(type(record['close_calls']) is list and len(record['close_calls'])==2
            and all(uint(value,1) for value in record['close_calls']),'two bounded handle close counters required')
    blocked=record['early_audit_blocked']
    require(blocked is None or type(blocked) is list and len(blocked)<=4096
        and all(type(value) is str and len(value)<=4096 for value in blocked),'bounded early audit messages required')
    require(uint(record['source_bookends'],1024) and uint(record['retained_modules'],4096),'bounded source/retention counts required')
    if record['graph_calls'] is not None:require(uint(record['graph_calls'],43),'bounded graph counter required')
    if record['namespace_terminal'] is not None:namespace_shape(record['namespace_terminal'])
    if record['construction_result'] is not None:construction_shape(record['construction_result'])
    if record['guard'] is not None:
        guard=record['guard'];require(type(guard) is dict and set(guard)==parent.GUARD_KEYS,'closed input guard fields required')
        for key in ('source_open_attempts','protected_open_attempts','write_attempts','process_attempts','sentinel'):
            require(uint(guard[key],1000000),'bounded input guard counters required')
        for key in ('events','faults'):require(type(guard[key]) is list and len(guard[key])<=4096
            and all(type(v) is str and len(v)<=4096 for v in guard[key]),'bounded input guard messages required')
    if record['boundary_report'] is not None:
        br=record['boundary_report'];require(type(br) is dict and set(br)==parent.BOUNDARY_KEYS,'closed boundary report fields required')
        require(br['schema']=='staged_saved_F_successor_import_boundary_report_v1' and br['authority']=='DRAFT_NONAUTHORITATIVE',
            'boundary schema differs')
        require(all(br[key] is False for key in parent.BOUNDARY_FALSE),'boundary authority differs')
    return record


def decode(parent,stdout):
    require(type(stdout) is bytes and len(stdout)<=131072,'probe stdout cap')
    record=unique_json(stdout);require(canonical(record)+b'\n'==stdout,'complete canonical probe line required')
    record_shape(parent,record)
    if record['import_profile'] is not None:profile_data(record['import_profile'])
    return record


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


def context(parent,case,code,argv):
    require(case in ('discovery','import_discovery') and type(code) is bytes,'construction manifest case required')
    path=parent.OUT/('probe_'+case+'.plan.json');raw=path.read_bytes()
    require(len(raw)<=131072,'manifest byte cap');plan=unique_json(raw)
    require(canonical(plan)==raw and plan['case']==case,'same canonical manifest required')
    parent.validate_manifest_pair(plan,code)
    expected=[str(parent.EXE),'-P','-B','-s','-S','-c',code.decode('utf8'),'--pre-entry-lease',str(path),pin(raw)['sha256']]
    require(argv==expected and len(subprocess.list2cmdline(argv).encode('utf-16-le'))//2<=30000,'exact released command differs')
    contract=dict(schema='staged_saved_F_construction_graph_contract_v1',calls=43,
        kinds=dict(namespace=33,adapter=10),intervals=INTERVALS)
    require(canonical(plan['graph_contract'])==canonical(contract),'exact graph DAG contract required')
    value=dict(manifest_pin=pin(raw),transport_pin=pin(code),source_epoch=plan['source_epoch'],
        source_pins_pin=pin(canonical(plan['source_pins'])),helpers_pin=pin(canonical(plan['producer_helpers'])),
        graph_contract_pin=pin(canonical(contract)),environment_pin=pin(canonical(plan['environment'])))
    return raw,plan,value


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


def validate_success(parent,record,parsed,plan,code):
    require(record['primary'] is None and record['secondary']==[] and record['failure_phase'] is None
        and record['dll_directory_close_returned'] is True and record['early_audit_blocked']==[],'successful close/error chain required')
    require(record['namespace_alias_absent'] is True and record['runtime_was_live'] is False,'unadmitted episode required')
    if plan['case']=='discovery':
        require(record['status']=='discovery_only' and record['startup_profile'] is not None,'startup discovery record required')
        for key in ('runtime_phase_before_close','runtime_phase','resource_phase','inputs_phase','namespace_phase','source_phase',
                'kernel_identity','close_calls','self_handles_closed','boundary_phase','boundary_report','post_metrics','graph_calls',
                'construction_result','namespace_terminal','guard','import_profile'):
            require(record[key] is None,'discovery opened runtime state: '+key)
        require(record['source_bookends']==record['retained_modules']==0,'discovery consumed source inputs')
        require(all(record[key] is False for key in ('runtime_is_resource_owner','old_inputs_successor_matches',
            'old_namespace_successor_matches')),'discovery cannot own a runtime successor')
        require(not parsed['stages'] and not parsed['graph_frames'] and not parsed['census_frames']
            and parsed['non_stage_pin']==pin(b''),'discovery stderr must be empty')
        startup_shape(parent,record['startup_profile'],plan,code)
        return dict(accepted=True,mode='startup_discovery_closed',construction_observed=False)
    require(record['status']=='completed' and record['runtime_phase_before_close']=='OBSERVED'
        and record['runtime_phase']==record['resource_phase']=='CLOSED'
        and record['source_phase']==record['inputs_phase']==record['namespace_phase']=='CONSUMED',
        'complete unadmitted runtime terminal phases required')
    require(all(record[key] is True for key in ('runtime_is_resource_owner','old_inputs_successor_matches','old_namespace_successor_matches',
        'self_handles_closed')) and record['close_calls']==[1,1] and all(type(v) is int for v in record['close_calls']),
        'original self handles and handoff required')
    require(record['source_bookends']==7 and 0<record['retained_modules']<=4096,'construction bookend/retention count differs')
    require(record['startup_profile'] is None and record['import_profile'] is not None,'independent unadmitted import observation required')
    profile=profile_data(record['import_profile'])
    wanted={name[:-3].replace('/','.').removesuffix('.__init__'):str(parent.ROOT/name)
        for name in plan['source_pins'] if name.startswith('src/') and name.endswith('.py')
            or name=='experiments/staged_rts24_saved_fresh_adoption_v1.py'}
    observed={row[0]:row[2] for row in profile['modules'] if len(row)==5 and type(row[2]) is str
        and Path(row[2]).is_relative_to(parent.ROOT)}
    require(len(wanted)==37 and observed==wanted,'complete selected project metadata differs')
    namespace_shape(record['namespace_terminal'],success=True);construction_shape(record['construction_result'])
    guard=record['guard'];require(guard is not None and guard['sentinel']==1 and guard['faults']==[]
        and guard['source_open_attempts']>0 and all(guard[key]==0 for key in ('protected_open_attempts','write_attempts','process_attempts')),
        'clean input guard observation required')
    events=guard['events'];require(events.index('self_handles_live')<events.index('source_read_begin')
        <events.index('transfer_committed')<events.index('self_handles_closed'),'owner event order differs')
    br=record['boundary_report'];require(br is not None and record['boundary_phase']==br['phase']=='CLOSED' and br['fault_kind']==''
        and br['machinery_observed_stage']==br['machinery_authenticated_stage']==2
        and br['machinery_authentication_pending'] is False and br['violations']==0,'completed import boundary required')
    for key in ('callback_retained','hook_installation_observed','finder_function_mutation_guard_installed',
            'finder_function_metadata_bookend_verified','forced_numpy_SVE_false','source49_bookend_equal','import_boundary_completed'):
        require(br[key] is True,'boundary success flag differs: '+key)
    for key in ('optional_Popen_attempts','blocked_optional_attempts','installation_sentinel_observed','audit_handoff_observed'):
        require(type(br[key]) is int and br[key]==1,'boundary counter differs')
    require(uint(br['internal_introspection_events'],4096),'introspection counter cap')
    metrics=record['post_metrics'];require(type(metrics) is dict and set(metrics)=={'returned','idle_getter_events','busy_getter_events',*METRICS}
        and metrics['returned'] is True,'closed post-return metrics required')
    for key,count in (('authenticate',1),('finder_check',16),('adapter_check',9),('profile',2)):
        row=metrics[key];require(type(row) is list and len(row)==3 and type(row[0]) is int and row[0]==count
            and all(type(v) is float and math.isfinite(v) and v>=0 for v in row[1:]) and row[2]<=row[1],'metric counter differs: '+key)
    require(uint(metrics['idle_getter_events'],1000000) and metrics['idle_getter_events']>0
        and uint(metrics['busy_getter_events'],1000000),'getter counter cap')
    require(record['graph_calls']==43 and parsed['graph_counts']==dict(namespace=33,adapter=10)
        and parsed['graph_intervals']==INTERVALS and len(parsed['graph_frames'])==86
        and all(row[5] is not None for row in parsed['graph_frames'] if row[3]=='exit'), 'complete graph DAG differs')
    require(parsed['graph_complete'] and parsed['stage_parse_complete'] and not parsed['stack_present']
        and [row[1] for row in parsed['stages']]==list(STAGES),'complete stage/graph trace required')
    require(parsed['census_stage_intervals']==['before_adapter_import','adapter_import_returned']
        and parsed['census_frames'],'bounded import census required')
    first,last=parsed['census_frames'][0],parsed['census_frames'][-1]
    require(last['reason']=='import_return_before2048' and last['active'] is False and last['inflight'] is False
        and last['passed']==last['entered']==last['observed'] and last['rejected']==last['diagnostic_error_count']==0
        and last['machinery_stage']==2,'successful census terminal required')
    require(parsed['stages'][1][2]<=first['start_clock']<=last['snapshot_clock']<=parsed['stages'][3][2],
        'census import time window differs')
    return dict(accepted=True,mode='unadmitted_construction_closed',construction_observed=True,
        graph_counts=parsed['graph_counts'],source_bookends=7,profile_pin=record['import_profile']['raw_pin'])


def compare(parent,case,code,stdout,stderr,child_code,identity,argv,writer_errors):
    require(not writer_errors,'release writer failed')
    require(child_code is None or type(child_code) is int,'exact child return code required')
    _,plan,before=context(parent,case,code,argv);parsed=parse(parent,stderr)
    record=None if not stdout else decode(parent,stdout);complete=False;witness=False;outcome=None
    if record is not None:
        require(record['case']==case or record['case'] is None and record['status']=='failed'
            and record['failure_phase']=='MANIFEST','child case differs')
        if child_code==0:
            outcome=validate_success(parent,record,parsed,plan,code);complete=True
        else:
            require(child_code==1 and record['status']=='failed' and (record['primary'] is not None or record['secondary']),
                'failed child must retain its exception chain')
        if record['kernel_identity'] is not None:kernel_match(parent,record,identity,argv)
        elif case!='discovery' and complete:raise ValueError('kernel observation missing')
        witness=record['self_handles_closed'] is True and record['close_calls']==[1,1]
    _,_,after=context(parent,case,code,argv);require(before==after,'manifest/helper context changed during parse')
    return dict(input_context=before,child_record=record,diagnostic=parsed,terminal_outcome=outcome,
        post_return_terminal_complete=complete,self_close_witness_present=witness,diagnostic_only=True,
        parent_python_graph_attested=False,producer_capability_verified=False,resource_admission=False,formal_result=False,actual_F=False)


def terminal_complete(result,reason):
    return reason is None and type(result) is dict and result.get('post_return_terminal_complete') is True


def audit(parent,row,published=True):
    """Reopen original bytes after the parent has observed child/pipe quiet."""
    require(type(row) is dict and set(row)==RECEIPT_FIELDS and row['schema']=='staged_saved_F_construction_parent_receipt_v1'
        and row['authority']=='DRAFT_NONAUTHORITATIVE','construction receipt required')
    require(row['accepted'] is True and row['primary'] is None and row['cleanup']==[]
        and type(row['child_exit']) is int and row['child_exit']==0 and row['drain_reason'] is None,'accepted complete receipt required')
    require(type(row['charged_seconds']) is float and math.isfinite(row['charged_seconds'])
        and type(row['cap_seconds']) in (int,float) and not isinstance(row['cap_seconds'],bool)
        and math.isfinite(row['cap_seconds']) and 0<row['cap_seconds']
        and 0<=row['charged_seconds']<=row['cap_seconds'],'receipt charge/cap differs')
    require(uint(row['parent_controller_pid'],4294967295) and row['parent_controller_pid']>0,'exact parent controller pid required')
    for key in ('parent_process_handle_closed','writer_thread_terminal','stdin_closed','release_sent'):
        require(row[key] is True,'parent terminal evidence missing: '+key)
    require(row['writer_errors']==[] and all(row[key] is False for key in FLAGS),'receipt authority/writer differs')
    stdout=base64.b64decode(row['stdout_raw_base64'],validate=True);stderr=base64.b64decode(row['stderr_raw_base64'],validate=True)
    require(pin(stdout)==row['stdout_pin'] and pin(stderr)==row['stderr_pin'],'saved stream pin differs')
    code=parent.transport();case=row['case'];path=parent.OUT/('probe_'+case+'.plan.json');raw=path.read_bytes()
    require(pin(raw)==row['plan_pin']==row['expected_manifest_pin'] and pin(code)==row['transport_pin'],'saved manifest/transport differs')
    argv=[str(parent.EXE),'-P','-B','-s','-S','-c',code.decode('utf8'),'--pre-entry-lease',str(path),pin(raw)['sha256']]
    result=compare(parent,case,code,stdout,stderr,row['child_exit'],row['parent_kernel_identity'],argv,row['writer_errors'])
    require(result==row['result'] and terminal_complete(result,row['drain_reason']),'saved terminal replay differs')
    require(row['context_before']==row['context_after']==result['input_context'],'parent before/after context differs')
    parent.validate_memory_observation(row['memory_observation'])
    require(pin(parent.DRAIN.read_bytes())==dict(bytes=14253,sha256='e0c54dc42657c223a81e7df8e2316289de58f95ce60457080b27fdf52931bc2d'),
        'same frozen memory/drain reader required')
    monitor=parent.load(parent.DRAIN,'_construction_saved_memory_guard');drain=row['bounded_drain']
    guard=monitor.validate_guard(drain['memory_guard'])
    require(guard['binding']['child_pid']==drain['direct_child_pid']==row['parent_kernel_identity']['pid']
        and guard['binding']['parent_pid']==row['parent_controller_pid'],'same sampled process pair required')
    require(row['memory_observation_source']=='last_live_memory_guard'
        and row['memory_observation']==dict(peak_working_set_bytes=guard['maxima']['child']['peak_working_set_bytes'],error=None),
        'same live memory observation required')
    require(drain['killed'] is False and drain['pipes_closed'] is True and drain['reader_threads_terminal'] is True
        and drain['reader_errors']==drain['cleanup']==[] and drain['stdout_truncated'] is False and drain['stderr_truncated'] is False,
        'bounded drain is not terminal')
    if published:
        case=row['case'];target=parent.OUT/('startup_profile.json' if case=='discovery' else 'import_profile.json')
        value=result['child_record']['startup_profile'] if case=='discovery' else profile_data(result['child_record']['import_profile'])
        expected=dict(path=str(target),pin=pin(canonical(value)))
        require(row['profile_publication']==expected and target.read_bytes()==canonical(value),'published profile differs from saved terminal')
    else:require(row['profile_publication'] is None,'profile must follow parent terminal validation')
    return result


def publish_profile(parent,row,owned=None):
    """Publish data only after complete parent terminal replay; create-only."""
    result=audit(parent,row,published=False);record=result['child_record'];case=row['case']
    value=record['startup_profile'] if case=='discovery' else profile_data(record['import_profile'])
    path=parent.OUT/('startup_profile.json' if case=='discovery' else 'import_profile.json')
    raw=canonical(value);require(len(raw)<=1048576,'published profile byte cap')
    if owned is None:owned=[None]
    require(type(owned) is list and len(owned)==1 and owned[0] is None,'new profile ownership slot required')
    with path.open('xb') as stream:
        info=os.fstat(stream.fileno());owned[0]=(path,info.st_dev,info.st_ino)
        stream.write(raw)
    require(path.read_bytes()==raw,'published profile readback differs')
    return dict(path=str(path),pin=pin(raw))


def retire_profile(parent,owned):
    """Preserve only this invocation's new file after a rejected publication."""
    path,device,inode=owned[0]
    require(path.parent==parent.OUT and path.name in ('startup_profile.json','import_profile.json'),'original profile path required')
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400
        and (info.st_dev,info.st_ino)==(device,inode),'newly created profile identity changed')
    target=path.with_name(path.stem+'.rejected.json')
    require(not os.path.lexists(target),'create-only rejected profile target required')
    # os.rename on this Windows workspace fails if the destination exists.
    os.rename(path,target);owned[0]=None
    raw=target.read_bytes();require(len(raw)<=1048576,'rejected profile byte cap')
    return dict(path=str(target),pin=pin(raw),adopted=False)


def finalize_profile(parent,row,started,seconds,clock):
    """Resolve publication and its final charge before the receipt is saved."""
    owned=[None]
    if row['accepted']:
        try:row['profile_publication']=publish_profile(parent,row,owned=owned)
        except BaseException as error:
            row['accepted']=False;row['primary']='profile_publication:'+type(error).__name__+':'+str(error)[:160]
    row['charged_seconds']=clock()-started
    if row['charged_seconds']>seconds:
        row['accepted']=False
        if row['primary'] is None:row['primary']='parent_phase_cap_exceeded'
    if not row['accepted'] and owned[0] is not None:
        try:row['profile_publication']=retire_profile(parent,owned)
        except BaseException as error:row['cleanup'].append('profile_retirement:'+type(error).__name__+':'+str(error)[:160])
        row['charged_seconds']=clock()-started
    return row
