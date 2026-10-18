"""Two fresh-process source calls on inactive chain06; preserve active chain07."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import psutil

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
saved=Path('D:/h1_chain_06_non_authoritative')
for proc in psutil.process_iter(['pid','name','cmdline']):
    if 'python' in (proc.info['name'] or '').lower():
        args=proc.info['cmdline'] or []
        if any('chain_06' in arg for arg in args):raise ValueError('saved input root still has a related Python process')
prior=json.loads((HERE/'parent_source_profile_plan_03.json').read_bytes())
sources={name:sha256(Path(name).read_bytes()).hexdigest() for name in prior['source_sha256']}
for path in (Path(__file__),HERE/'measure_parent_source_path_coverage_v1.py',
        HERE/'run_parent_source_path_coverage_bounded_v1.py'):
    raw=path.read_bytes();ast.parse(raw,filename=str(path));sources[str(path)]=sha256(raw).hexdigest()
for name,pin in prior['old_chain_sha256'].items():
    if sha256(Path(name).read_bytes()).hexdigest()!=pin:raise ValueError('active chain07 code changed')
saved_pins={str(path):sha256(path.read_bytes()).hexdigest() for path in saved.rglob('*')
    if path.is_file() and path.suffix!='.lock'}
snapshot=saved/'test_complete_independent_N0_r0/parent_non_authoritative/worker_non_authoritative/selector_snapshot.json'
binding=json.loads(snapshot.read_bytes())['declaration']['source_binding']
if not Path(binding['root']).is_relative_to(saved):raise ValueError('source controller leaves inactive root')
source_paths={Path(name):pin for name,pin in sources.items()}
if any(source_paths.get(Path(name))!=pin for name,pin in prior['code_lease_sha256'].items()):
    raise ValueError('source and code lease maps must match before launch')
for mode in ('baseline','candidate'):
    value={key:prior[key] for key in ('status','old_chain_sha256','code_lease_sha256')}
    value.update(question='Does the existing path lease cover the actual inactive source archive while preserving all source fields?',
        mode=mode,attempts=1,pair_total_attempts=2,total_source_prepares=2,
        new_simulated_hours=0,source_prefix_completed_hours=1,new_controller_roots=0,
        synthetic_jobs=0,native_calls=0,expected_saved_locks=0,
        source_sha256=sources,saved_root=str(saved),saved_inventory_roots=[str(saved)],saved_sha256=saved_pins,
        fixture_base=str(saved/'test_complete_independent_N0_r0'),snapshot=str(snapshot),
        inner_output=str(HERE/('parent_source_path_coverage_01_'+mode+'_non_authoritative')),
        outer_output=str(HERE/('parent_source_path_coverage_monitor_01_'+mode)),
        basetemp='D:/h1_parent_source_path_coverage_01_'+mode+'_non_authoritative',
        path_roots=[str(REPO)]+([str(saved)] if mode=='candidate' else []),
        path_cache_scope='repository plus inactive chain06 only' if mode=='candidate' else 'repository only',
        path_saved_root=str(saved),changed_input_reason='profile03 found 3453 path fallbacks because protected active chain07 was outside the repo-only scope; compare on inactive chain06',
        modes=['one_original_source_prepare'],baseline_source_prepares=1,candidate_source_prepares=0,
        source_profile_count=0,profiler_overhead_included=False,
        measured_call_scope='one unchanged core.prepare; no Parent inspection or credential',
        complete_Parent_validation=False,live_Parent_credential_issued=False,
        old_chain_policy='no active chain07 directory share handles, source writes, lifecycle action or code changes',
        dag=['two serial fresh processes with identical inactive source and fixed synthetic fixture',
            'baseline repo-only path lease versus candidate repo plus inactive archive',
            'one unchanged full exact-source call per process; save every declared field',
            'exact science/decision/audit/field comparison, path hits, handles, input and PID postchecks'],
        stop_conditions=['one call per mode; 120s wall, sampled RSS 768MiB, storage 128MiB',
            'fail on origins, path ordering, source fields or cleanup mismatch; no deadline extension'],
        limits=dict(wall_seconds=120,sampled_rss_bytes=768*1024**2,storage_bytes=128*1024**2))
    for key in ('expected_decision_sha256','expected_audit_sha256','expected_complete_projection_sha256'):
        value.pop(key,None)
    path=HERE/('parent_source_path_coverage_plan_01_'+mode+'.json')
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
    print(json.dumps(dict(mode=mode,plan_sha256=sha256(path.read_bytes()).hexdigest(),
        limits=value['limits'],saved_nonlock_files=len(saved_pins),path_roots=value['path_roots'])))
