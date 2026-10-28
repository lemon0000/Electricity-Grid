"""Bounded post-return development observations; no execution authority."""
import base64
import json
import math
import zlib

STAGES=('loader_ready','before_adapter_import','adapter_import_returned','after_adapter_import_attempt',
    'before_machinery_authentication','machinery_authenticated','before_source_bytes','after_source_bytes',
    'before_adapter_roots','after_adapter_roots','before_final_source_bookend','after_final_source_bookend',
    'before_retention','after_retention','before_boundary_close','after_boundary_close','before_profile','after_profile',
    'before_finish_import','after_finish_import',
    'before_final_runtime_close','after_final_runtime_close')
METRICS=('authenticate','finder_check','adapter_check','profile')
GRAPH_CALL_CAP=40
GRAPH_IMAGE_CAP=4194304


def parse(parent,raw):
    assert type(raw) is bytes and len(raw)<=32768
    normalized=[];frames=[];pending=None;calls=0;previous=-1.0;stage='<before_loader_ready>';intervals={};census_stages=[]
    for line in raw.splitlines(keepends=True):
        try:row=json.loads(line)
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
            assert type(clock) is float and math.isfinite(clock) and previous<=clock<=1e12
            previous=clock;normalized.append(line);continue
        if row[0]!='graph':normalized.append(line);continue
        assert parent.canonical(row)+b'\n'==line and len(row) in (5,8)
        _,seq,kind,state,clock,*sizes=row
        assert type(seq) is int and 1<=seq<=GRAPH_CALL_CAP and kind in ('namespace','adapter')
        assert type(clock) is float and math.isfinite(clock) and previous<=clock<=1e12
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
    return parsed


def validate_success(record,parsed,parent):
    record_shape(parent,record)
    assert record['schema']=='staged_saved_F_runtime_handoff_probe_v2' and record['status']=='completed'
    assert record['primary'] is None and record['secondary']==[]
    assert record['runtime_phase_before_close']=='LIVE' and record['runtime_phase']=='CLOSED' and record['resource_phase']=='CLOSED'
    assert record['runtime_was_live'] is True and record['boundary_phase']=='CLOSED'
    assert type(record['source_bookends']) is int and record['source_bookends']==5
    assert type(record['retained_modules']) is int and 0<record['retained_modules']<=4096 and record['import_profile'] is not None
    profile_shape(record['import_profile'])
    assert record['self_handles_closed'] is True and record['close_calls']==[1,1] and all(type(n) is int for n in record['close_calls']) and record['dll_directory_close_returned'] is True
    assert record['failure_phase'] is None and record['startup_profile'] is None
    br=record['boundary_report']
    assert br['machinery_observed_stage']==br['machinery_authenticated_stage']==2
    assert br['machinery_authentication_pending'] is False and br['source49_bookend_equal'] is True
    assert br['import_boundary_completed'] is True and br['violations']==0
    assert br['phase']=='CLOSED' and br['fault_kind']==''
    for key in ('callback_retained','hook_installation_observed','finder_function_mutation_guard_installed','finder_function_metadata_bookend_verified','forced_numpy_SVE_false'):assert br[key] is True
    for key in ('optional_Popen_attempts','blocked_optional_attempts','installation_sentinel_observed','audit_handoff_observed'):assert type(br[key]) is int and br[key]==1
    assert type(br['internal_introspection_events']) is int and 0<=br['internal_introspection_events']<=4096
    guard=record['guard'];assert guard['faults']==[] and record['early_audit_blocked']==[]
    assert type(guard['source_open_attempts']) is int and guard['source_open_attempts']>0
    assert type(guard['sentinel']) is int and guard['sentinel']==1
    for key in ('protected_open_attempts','write_attempts','process_attempts'):assert type(guard[key]) is int and guard[key]==0
    assert type(guard['events']) is list and all(type(v) is str for v in guard['events'])
    assert guard['events'].index('self_handles_live')<guard['events'].index('source_read_begin')<guard['events'].index('transfer_committed')<guard['events'].index('self_handles_closed')
    metrics=record['post_metrics']
    assert type(metrics) is dict and set(metrics)=={'returned','idle_getter_events','busy_getter_events',*METRICS}
    assert metrics['returned'] is True
    for name,count in (('authenticate',1),('finder_check',10),('adapter_check',8),('profile',2)):
        row=metrics[name]
        assert type(row) is list and len(row)==3 and type(row[0]) is int and row[0]==count
        assert all(type(t) is float and math.isfinite(t) and t>=0 for t in row[1:]) and row[2]<=row[1]
    assert type(metrics['idle_getter_events']) is int and 0<metrics['idle_getter_events']<=1000000
    assert type(metrics['busy_getter_events']) is int and 0<=metrics['busy_getter_events']<=1000000
    assert type(record['graph_calls']) is int and record['graph_calls']==30 and parsed['graph_counts']==dict(namespace=21,adapter=9)
    assert parsed['graph_complete'] and parsed['stage_parse_complete'] and not parsed['stack_present']
    assert [r[1] for r in parsed['stages']]==list(STAGES)
    assert all(a[2]<=b[2] for a,b in zip(parsed['stages'],parsed['stages'][1:]))
    assert len(parsed['graph_frames'])==60 and all(r[5] is not None for r in parsed['graph_frames'] if r[3]=='exit')
    n,a='namespace','adapter'
    assert parsed['graph_intervals']=={'<before_loader_ready>':[n]*15,'before_source_bytes':[n],'before_adapter_roots':[a],
        'before_boundary_close':[a,a],'before_profile':[a],'before_finish_import':[n,a,a,n,a,n,a],
        'before_final_runtime_close':[n,a,n]}
    assert parsed['census_stage_intervals']==['before_adapter_import','adapter_import_returned']
    assert parsed['census_frames']
    first,last=parsed['census_frames'][0],parsed['census_frames'][-1]
    assert last['reason']=='import_return_before2048' and last['active'] is False and last['inflight'] is False
    assert 0<=last['passed']<2048 and last['passed']==last['entered']==last['observed']
    assert last['rejected']==last['diagnostic_error_count']==0 and last['machinery_stage']==2
    start=parsed['stages'][1][2];finished=parsed['stages'][3][2]
    assert start<=first['start_clock']<=last['snapshot_clock']<=finished
    assert all(first['start_clock']<=r['snapshot_clock']<=last['snapshot_clock'] for r in parsed['census_frames'])
    comparison=parent.REFERENCE.compare_profile(record['import_profile'])
    assert comparison['frozen_nfc9_import_profile_exact_match'] is True
    assert comparison['expected_import_profile_pin']==comparison['observed_import_profile_pin']
    return dict(expected_import_profile_pin=comparison['expected_import_profile_pin'],observed_import_profile_pin=comparison['observed_import_profile_pin'],frozen_nfc9_import_profile_exact_match=True,accepted=True,terminal_mode='post_return_live_closed',passed=last['passed'],importer_return_observed=True,
        live_before_close=True,boundary_completed=True,graph_counts=parsed['graph_counts'],source_bookends=5,
        selected_open_window_only=True,all_unselected_events_verified=False,candidate_adopted=False,resource_admission=False)


def record_shape(parent,record):
    assert type(record) is dict and set(record)==parent.RECORD_KEYS|{'runtime_phase_before_close','post_metrics','graph_calls'}
    assert record['schema']=='staged_saved_F_runtime_handoff_probe_v2' and record['authority']=='DRAFT_NONAUTHORITATIVE'
    assert record['case']=='normal' and record['source_epoch']==parent.SOURCE_SHA
    assert all(record[k] is False for k in parent.FALSE_FIELDS) and record['live_at_report'] is False
    guard=record['guard'];assert type(guard) is dict and set(guard)==parent.GUARD_KEYS
    br=record['boundary_report'];assert type(br) is dict and set(br)==parent.BOUNDARY_KEYS
    assert br['schema']=='staged_saved_F_successor_import_boundary_report_v1' and br['authority']=='DRAFT_NONAUTHORITATIVE'
    assert all(br[k] is False for k in parent.BOUNDARY_FALSE)
    parent.validate_exception_images([record['primary'],*record['secondary']])


def decode(parent,stdout):
    record=json.loads(stdout);assert parent.canonical(record)+b'\n'==stdout
    record_shape(parent,record)
    if record['import_profile'] is not None:
        encoded=record['import_profile']
        assert type(encoded) is dict and set(encoded)=={'encoding','raw_pin','data'} and encoded['encoding']=='zlib_base64'
        raw=base64.b64decode(encoded['data'],validate=True);unpacker=zlib.decompressobj();raw=unpacker.decompress(raw,1048577)
        assert len(raw)<=1048576 and unpacker.eof and not unpacker.unconsumed_tail and not unpacker.unused_data and parent.pin(raw)==encoded['raw_pin']
        profile=json.loads(raw);assert parent.canonical(profile)==raw;profile_shape(profile);record['import_profile']=profile
    return record


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


def compare(parent,case,code,stdout,stderr,child_code,identity,argv,writer_errors):
    if case=='discovery':return parent.base_compare_child(case,code,stdout,stderr,child_code,identity,argv,writer_errors)
    assert case=='normal' and not writer_errors
    manifest_raw=(parent.OUT/'probe_normal.plan.json').read_bytes();plan=json.loads(manifest_raw)
    assert argv[-2:]==[str(parent.OUT/'probe_normal.plan.json'),parent.pin(manifest_raw)['sha256']]
    reference_context=parent.REFERENCE.context(parent,code,plan,manifest_raw)
    parsed=parse(parent,stderr)
    record=None;witness=False;complete=False
    if stdout:
        record=decode(parent,stdout)
        witness=record['self_handles_closed'] is True and record['close_calls']==[1,1] and record['dll_directory_close_returned'] is True
        if child_code==0:
            validate_success(record,parsed,parent)
            record=parent.base_compare_child(case,code,stdout,b'',child_code,identity,argv,writer_errors)['child_record']
            complete=True
        else:
            assert child_code==1 and record['status']=='failed' and record['primary'] is not None
            parent.validate_exception_images([record['primary'],*record['secondary']])
    comparison=parent.REFERENCE.compare_profile(None if record is None else record['import_profile'])
    return dict(reference_context=reference_context,profile_comparison=comparison,child_record=record,diagnostic=parsed,self_close_witness_present=witness,adapter_import_attempts_upper_bound=1,
        adapter_import_return_observed=any(r[1]=='adapter_import_returned' for r in parsed['stages']),prefix_complete=False,
        post_return_terminal_complete=complete,census_terminal_reason=parsed['census_frames'][-1]['reason'] if parsed['census_frames'] else 'no_census',
        diagnostic_only=True)


def terminal_complete(result,reason):
    return reason is None and type(result) is dict and result.get('post_return_terminal_complete') is True


def audit(parent,row):
    assert row['accepted'] is True and row['child_exit']==0 and row['drain_reason'] is None
    r=row['result'];record=r['child_record']
    raw=base64.b64decode(row['stderr_raw_base64'],validate=True);stdout=base64.b64decode(row['stdout_raw_base64'],validate=True)
    assert parent.pin(raw)==row['stderr_pin'] and parent.pin(stdout)==row['stdout_pin']
    assert decode(parent,stdout)==record
    manifest_raw=(parent.OUT/'probe_normal.plan.json').read_bytes();plan=json.loads(manifest_raw)
    assert parent.pin(manifest_raw)==row['plan_pin']==row['expected_manifest_pin']
    context=parent.REFERENCE.context(parent,parent.transport(),plan,manifest_raw)
    assert row['reference_before']==row['reference_after']==r['reference_context']==context
    assert row['transport_pin']==context['transport_pin']
    assert r['profile_comparison']==parent.REFERENCE.compare_profile(record['import_profile'])
    parsed=parse(parent,raw);assert parsed==r['diagnostic']
    result=validate_success(record,parsed,parent);assert r['post_return_terminal_complete'] and r['self_close_witness_present']
    parent.validate_memory_observation(row['memory_observation'])
    monitor=parent.load(parent.DRAIN,'_post_return_memory_audit');drain=row['bounded_drain'];guard=monitor.validate_guard(drain['memory_guard'])
    assert guard['binding']['child_pid']==drain['direct_child_pid']==row['parent_kernel_identity']['pid']
    assert guard['binding']['parent_pid']==row['parent_controller_pid']
    assert row['memory_observation_source']=='last_live_memory_guard'
    assert row['memory_observation']==dict(peak_working_set_bytes=guard['maxima']['child']['peak_working_set_bytes'],error=None)
    assert not drain['killed'] and drain['pipes_closed'] and drain['reader_threads_terminal'] and not drain['reader_errors'] and not drain['cleanup']
    assert not drain['stdout_truncated'] and not drain['stderr_truncated']
    assert row['parent_process_handle_closed'] and row['writer_thread_terminal'] and row['stdin_closed'] and not row['writer_errors'] and not row['cleanup']
    assert len(stdout)<=131072 and len(raw)<=32768
    for key in parent.FALSE_FIELDS:assert row[key] is False and record[key] is False
    return result
