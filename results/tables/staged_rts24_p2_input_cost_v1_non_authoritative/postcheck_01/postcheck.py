"""Independent saved-byte/profile checks; never import research or run targets."""
import ast
from hashlib import sha256
import json
import marshal
import math
from pathlib import Path
import re
import stat

ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent.parent
POST=BASE/'postcheck_01'
MEASURE=BASE/'measure_01'
CHECKS=BASE/'development_checks_01'
LABELS=('fingerprints','packet','preserve')
P1=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
PRIOR=P1.parent/'p1_execution_review_01/postcheck_03.stdout.json'


def require(value,message):
    if not value:raise ValueError(message)


def read(path):return json.loads(path.read_bytes())


def digest(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def stamp(path,repository=True):
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
        and not getattr(info,'st_file_attributes',0)&0x400 and (not repository or info.st_nlink==1),'nonordinary file')
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def function_target(path,name):
    tree=ast.parse(path.read_text(encoding='utf-8-sig'))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name]
    require(len(nodes)==1,'target AST ambiguity')
    return str(path),nodes[0].lineno,name


def profile_check(label,wall):
    stats=read(MEASURE/(label+'_stats.json'))
    require(set(stats)=={'profiled_wall_seconds','function_count','target_calls','target_primitive_calls','top_self','top_cumulative','target','scope'},'stats schema')
    require(type(wall) in (int,float) and math.isfinite(wall) and wall>=0 and stats['profiled_wall_seconds']==wall,'profile wall')
    target=function_target(ROOT/'experiments/staged_rts24_p2_native_probe_v1.py','load_packet' if label=='packet' else label)
    require(stats['target']==dict(zip(('file','line','name'),target)),'original target identity')
    with (MEASURE/(label+'.prof')).open('rb') as stream:
        data=marshal.load(stream);require(stream.read()==b'','profile trailing data')
    rows=[dict(file=k[0],line=k[1],function=k[2],primitive_calls=v[0],calls=v[1],self_seconds=v[2],cumulative_seconds=v[3]) for k,v in data.items()]
    require(rows and len(rows)==stats['function_count'] and data[target][:2]==(1,1)
        and stats['target_calls']==stats['target_primitive_calls']==1,'profile target count')
    require(all(type(r['file']) is type(r['function']) is str and type(r['line']) is int
        and all(type(r[n]) is int and r[n]>=0 for n in ('primitive_calls','calls'))
        and all(type(r[n]) in (int,float) and math.isfinite(r[n]) and r[n]>=0 for n in ('self_seconds','cumulative_seconds')) for r in rows),'profile row values')
    require(stats['top_self']==sorted(rows,key=lambda r:r['self_seconds'],reverse=True)[:80]
        and stats['top_cumulative']==sorted(rows,key=lambda r:r['cumulative_seconds'],reverse=True)[:80],'raw profile/summary mismatch')
    if label!='packet':
        legacy=function_target(ROOT/'experiments/staged_rts24_native_probe_v1.py',label)
        require(data[legacy][:2]==(1,1),'nested original target count')
    return dict(profiled_wall_seconds=wall,function_count=len(rows),target_calls=1)


def main():
    preserved=read(POST/'prior_preservation_inventory.json')
    require(len(preserved)==294 and all(stamp(ROOT/n)==v for n,v in preserved.items()),'previous publication drift')
    for label,count in (('units_04',33),('related_01',68)):
        record=read(CHECKS/(label+'.exit.json'))
        require(record['exit_code']==0 and record['source_pins_unchanged'] is True
            and all(stamp(ROOT/n)==v for n,v in record['source_pins'].items()),'ordinary checks/source drift')
        require((CHECKS/(label+'.stderr.log')).read_bytes()==b'' and re.search(rb'\b'+str(count).encode()+rb' passed in\b',
            (CHECKS/(label+'.stdout.log')).read_bytes()),'ordinary check summary')
    prereview=read(CHECKS/'prereview_01.json')
    require(prereview['remaining_high_medium']==[] and all(prereview[n] is None for n in ('official_verdict','review_receipt','seal')),'review authority')
    start=read(MEASURE/'start.json');pins=start['source_pins']
    require(len(pins)==66 and all(stamp(ROOT/n)==v for n,v in pins.items()),'66 source bindings')
    require(start['native_authorized'] is False and start['fixed_target_calls']=={n:1 for n in LABELS},'diagnostic scope')
    require(start['limits']==dict(wall_seconds=60,no_progress_seconds=30,rss_bytes=536870912,output_bytes=16777216,files=64),'diagnostic caps')
    required={'start.json','events.jsonl','worker.stdout.log','worker.stderr.log','runtime_before.json','runtime_after.json','observations.json','report.json'}|{n+s for n in LABELS for s in ('.prof','_stats.json')}
    require({p.name for p in MEASURE.iterdir()}==required|{'postquiet.json','launcher.json'},'measurement file set')
    inventory={n:stamp(MEASURE/n) for n in required}
    attempt=read(POST/'measurement_inventory.json')
    require(attempt=={p.name:stamp(p) for p in MEASURE.iterdir()},'saved measurement changed')
    adopted=read(MEASURE/'postquiet.json')
    require(adopted==dict(output_pins=inventory,P1_rechecked_after_quiet=True,source_pins_sha=digest(pins)),'postquiet adopted pins')
    runtime=read(MEASURE/'runtime_before.json')
    require(inventory['runtime_before.json']==inventory['runtime_after.json'],'runtime bookend bytes')
    require(len(runtime['applications'])==39 and len(runtime['functions'])==33,'selected runtime scope')
    for item in runtime['applications'].values():
        path=Path(item['path']);require(path.is_relative_to(ROOT) and stamp(path)==item['pin']==pins[path.relative_to(ROOT).as_posix()],'runtime application binding')
    for item in runtime['functions'].values():
        path=Path(item['path'])
        require(stamp(path,path.is_relative_to(ROOT))['sha256']==item['source_sha'] and re.fullmatch('[0-9a-f]{64}',item['code_sha']),'selected function source binding')
    require(runtime['controlled_environment_sha']=='5a8dfc180910127d8cee4587e94f27859db05295b950c1435182f788caaa4c37','controlled environment')
    require(stamp(Path('D:/Miniconda3/envs/compute/python.exe'),False)==runtime['executable'],'interpreter bytes')
    for name,pin in runtime['selected_profiler_stdlib'].items():
        if name=='_lsprof':require(pin==dict(origin='built-in',executable_bound=True),'built-in profiler binding')
        else:
            path=Path('D:/Miniconda3/envs/compute/Lib').joinpath(*name.split('.'))
            path=path/'__init__.py' if name=='json' else path.with_suffix('.py')
            require(stamp(path,False)==pin,'selected stdlib bytes')
    observed=read(MEASURE/'observations.json');names=observed['loaded_module_names']
    require(type(names) is list and all(type(n) is str for n in names) and names==sorted(set(names))==runtime['loaded_module_names']
        and len(names)==1929,'module inventory binding')
    require(set(runtime['applications'])<=set(names) and observed['module_inventory_unchanged'] is True
        and observed['guards_restored'] is True and observed['target_calls']=={n:1 for n in LABELS},'worker observations')
    require(len(start['forbidden_labels'])==38 and sorted(observed['forbidden_calls'])==start['forbidden_labels']
        and all(type(v) is int and v==0 for v in observed['forbidden_calls'].values()),'forbidden route observations')
    expected_events=[dict(stage='inputs_checked')]
    for n in LABELS:expected_events.extend((dict(stage='profile_started',label=n),dict(stage='profile_returned',label=n)))
    expected_events.append(dict(stage='complete'))
    require([json.loads(v) for v in (MEASURE/'events.jsonl').read_bytes().splitlines()]==expected_events,'event sequence')
    original=read(PRIOR);old=read(P1/'start.json');prep=ROOT/'results/tables/staged_rts24_p2_packet_v1_non_authoritative/packet_01'
    prep_pins={p.name:stamp(p) for p in prep.iterdir()};require(len(prep_pins)==3,'preparation inventory')
    context=read(prep/'context.json');direct=read(ROOT/'results/tables/staged_rts24_p2_runner_v1_non_authoritative/development_checks_01/units_03.exit.json')['source_pins']
    expected=dict(fingerprints=dict(legacy_scientific_and_P1_runtime=old['pins'],preparation_sources=context['source_pins'],P2_sources=direct,preparation_files=prep_pins),
        packet=read(prep/'packet.json'),preserve=dict(original=old['preserved'],P1_anchor=stamp(PRIOR),P2_preparation=prep_pins))
    shas={n:digest(v) for n,v in expected.items()}
    report=read(MEASURE/'report.json')
    fixed=dict(authority='DRAFT_NONAUTHORITATIVE',result_shas=shas,source_pins_sha=digest(pins),runtime_sha=digest(runtime),P1_files_unchanged=683,
        solver_calls=0,new_models=0,new_replays=0,native_authorized=False,formal_result=False,resource_admission=False,
        C_overall_performance_review_complete=False,scope='three original input checks once each; no P2 execution or speedup')
    require(set(report)==set(fixed)|{'profiled_seconds'} and digest({n:report[n] for n in fixed})==digest(fixed)
        and observed['result_shas']==shas and set(report['profiled_seconds'])==set(LABELS),'report result/scope binding')
    profiles={n:profile_check(n,report['profiled_seconds'][n]) for n in LABELS}
    launcher=read(MEASURE/'launcher.json');witness=launcher['quiescence_witness'];limits=start['limits']
    require(launcher['exit_code']==0 and launcher['job_quiet_confirmed'] is True
        and all(launcher[n] is None for n in ('stop_reason','monitor_error','cleanup_error')),'Job terminal failure')
    require(witness['active_processes']==0 and witness['final_pids']==[] and witness['all_handles_signaled'] is True
        and witness['complete_inventory'] is True and witness['observed_unique_member_handles']==witness['total_processes']==len(witness['member_identities'])==2,'Job ownership quiet witness')
    require(launcher['outer_seconds']<limits['wall_seconds'] and launcher['sampled_tree_peak_rss_bytes']<limits['rss_bytes']
        and launcher['peak_job_commit_bytes']<2*1024**3 and launcher['terminal_files']==14
        and launcher['terminal_bytes']==sum(v['bytes'] for v in inventory.values())<limits['output_bytes'],'diagnostic cap evidence')
    command=read(BASE/'execution_observations_01/command_01.exit.json')
    require(command['exit_code']==0 and command['source_pins_unchanged'] is True and command['source_pins']==prereview['source_pins'],'command terminal binding')
    require(all((BASE/'execution_observations_01'/('command_01.'+n+'.log')).read_bytes()==b'' for n in ('stdout','stderr')),'command output')
    require((MEASURE/'worker.stdout.log').read_bytes()==(MEASURE/'worker.stderr.log').read_bytes()==b'','worker output')
    require({p.relative_to(P1).as_posix():stamp(p) for p in P1.rglob('*') if p.is_file()}==original['p1_files'],'original P1 changed')
    for name,anchor in (('P1_and_prior',PRIOR),('P2_preparation',ROOT/'results/tables/staged_rts24_p2_packet_v1_non_authoritative/postcheck_01/packet_03.stdout.json'),
        ('P2_runner',ROOT/'results/tables/staged_rts24_p2_runner_v1_non_authoritative/postcheck_01/runner_01.stdout.json')):
        record=read(POST/(name+'.exit.json'))
        require(record['exit_code']==0 and record['exact_prior_stdout'] is True and stamp(POST/(name+'.stdout.json'))==stamp(anchor)
            and (POST/(name+'.stderr.log')).read_bytes()==b'','prior stdlib stdout drift')
    native=ROOT/'results/tables/staged_rts24_p2_native_v1_non_authoritative'
    require(not (native/'p2_01').exists() and not (native/'registration_v1.json').exists(),'P2 execution appeared')
    require(all(stamp(ROOT/n)==v for n,v in pins.items()) and attempt=={p.name:stamp(p) for p in MEASURE.iterdir()},'final source/output bookend')
    return dict(authority='DRAFT_NONAUTHORITATIVE',script=stamp(Path(__file__)),profiles=profiles,source_files_unchanged=66,
        selected_app_modules=39,selected_functions=33,loaded_modules=1929,forbidden_routes_zero=38,Job_members_quiet=2,
        measurement_files=16,measurement_bytes=sum(v['bytes'] for v in attempt.values()),targeted_passed=33,related_passed=68,
        previous_publication_files_unchanged=294,P1_files_unchanged=683,P1_bytes_unchanged=2950863,
        B1_B3_saved_files=original['B1_B3_saved_files'],prior_checkpoint_paths=original['unique_prior_checkpoint_paths'],
        new_native_calls=0,new_scientific_replays_by_postcheck=0,formal_result=False,resource_admission=False,
        C_overall_performance_review_complete=False,scope='saved diagnostic profiles and byte bindings only; no target execution by postcheck')


if __name__=='__main__':print(json.dumps(main(),sort_keys=True,indent=2,allow_nan=False))
