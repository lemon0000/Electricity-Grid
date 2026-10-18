"""Fresh source/storage/PID readback of the four completed identity workers."""
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean
import psutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
root=HERE/'vendor_code_identity_pair_01'


def read(path):return json.loads(path.read_bytes())
def digest(path):return sha256(path.read_bytes()).hexdigest()


terminal=read(root/'terminal.json');plan=read(root/'plan.json')
tool=read(HERE/'vendor_code_identity_probe_tool_terminal.json')
assert tool['exit_code']==0 and terminal['exit_code']==0
assert terminal['completed_workers']==4 and terminal['planned_workers']==4
assert [row['mode'] for row in terminal['rows']]==plan['modes']==['baseline','vendor7','vendor7','baseline']
pins={};checks=[]
baseline=terminal['rows'][0]['result']
for index,row in enumerate(terminal['rows']):
    mode=row['mode'];worker=root/(str(index)+'_'+mode+'_non_authoritative')
    actual=read(root/(str(index)+'_'+mode+'_terminal.json'))
    assert row==actual and row['exit_code']==0 and row['stop_reason'] is None
    assert row['elapsed_seconds']<plan['per_child_wall_seconds']
    try:
        process=psutil.Process(row['pid'])
        assert process.create_time()!=row['creation_time'] or not process.is_running()
    except psutil.NoSuchProcess:pass
    request=read(worker/'request.json');result=read(worker/'result.json')
    assert result==row['result'] and result['source_unchanged']
    assert result['original_identity_functions_unchanged'] and result['stock_metadata_functions_unchanged']
    assert result['unlisted_mutable_file_fallback_observed'] and result['real_native_calls']==0
    assert result['vendor_module_origins']==baseline['vendor_module_origins']
    for name,target in baseline['targets'].items():
        assert result['targets'][name]['identity']==target['identity']
        assert result['targets'][name]['separate_single_call_profile_counts']==target['separate_single_call_profile_counts']
    lease=result['code_lease_receipt'];assert lease['file_count']==(149 if mode=='baseline' else 156)
    assert not lease['source_or_result_cache'] and not lease['numerical_result_cache']
    assert not lease['distribution_discovery_cached']
    assert len(result['vendor_hits'])==7
    assert sum(result['vendor_hits'].values())==(0 if mode=='baseline' else 1253)
    for name,pin in request['files_sha256'].items():
        path=Path(name)
        snapshot=(worker/'tested_bytes/repository'/path.relative_to(REPO) if path.is_relative_to(REPO)
            else worker/'tested_bytes/external'/path.drive[:1]/Path(*path.parts[1:]))
        assert digest(path)==pin and digest(snapshot)==pin
        pins[str(path)]=pin
    for path in (worker/'request.json',worker/'result.json',root/(str(index)+'_'+mode+'_terminal.json')):
        pins[str(path)]=digest(path)
    checks.append(dict(mode=mode,source_and_snapshot_files=len(request['files_sha256']),
        observed_direct_pid_absent=True,cache_files=lease['file_count'],vendor_hits=sum(result['vendor_hits'].values()),
        lease_setup_seconds=result['lease_setup_seconds']))
stats={}
for name in baseline['targets']:
    values={mode:mean(row['result']['targets'][name]['unprofiled_seconds'] for row in terminal['rows'] if row['mode']==mode)
        for mode in ('baseline','vendor7')}
    stats[name]=dict(**values,reduction_fraction=1-values['vendor7']/values['baseline'],
        iterations_per_worker=baseline['targets'][name]['iterations'])
storage=sum(path.stat().st_size for path in root.rglob('*') if path.is_file())
assert storage<plan['storage_cap_bytes'] and terminal['peak_sampled_rss_including_monitor']<plan['aggregate_sampled_rss_cap_bytes']
old=read(HERE.parent/'chain_07/request.json')['before']
assert all(digest(Path(name))==pin for name,pin in old.items())
for path in (Path(__file__),root/'terminal.json',root/'plan.json',HERE/'vendor_code_identity_probe_tool_terminal.json'):
    pins[str(path)]=digest(path)
output=dict(status='IDENTITY_ONLY_DIAGNOSTIC_TERMINAL_AND_READBACK_COMPLETE',workers=checks,
    timings=stats,fresh_post_terminal_storage_bytes=storage,post_terminal_storage_cap_satisfied=True,
    peak_sampled_rss_including_monitor=terminal['peak_sampled_rss_including_monitor'],
    source_and_evidence_pins=pins,old_chain_inputs_unchanged=len(old),
    complete_descendant_tree_absence_proven=False,process_scope='four directly observed worker PID+creation identities only',
    small_sample_limit='two fresh processes per mode; one bootstrap timed call per process; directional evidence',
    next_decision='test exact vendor entry admission and one saved real common._arm per configuration before another slice',
    full_chain_speedup_measured=False,full_hour0_chain_passed=False,formal_result=False,
    formal_execution_ready=False,resource_admission=False,native_execution_authorized=False)
path=HERE/'vendor_code_identity_postcheck_01.json'
with path.open('x',encoding='utf-8',newline='\n') as stream:json.dump(output,stream,indent=2)
print(json.dumps(dict(output=str(path),timings=stats,storage_bytes=storage,pins=len(pins))),flush=True)
