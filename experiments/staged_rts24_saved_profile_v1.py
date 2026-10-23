"""One bounded, solver-free profile of saved P1 verification and full replay."""
import argparse
import cProfile
from hashlib import sha256
import json
import marshal
import math
import os
from pathlib import Path
import pstats
import stat
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
BASE=ROOT/'results/tables/staged_rts24_saved_profile_v1_non_authoritative'
OUTPUT=BASE/'profile_01'
P1=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
PRIOR=P1.parent/'p1_execution_review_01/postcheck_03.stdout.json'
PRIOR_SHA='c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473'
CONTRACT=ROOT/'docs/plan/staged_deliverability_c_saved_profile_contract_v1.md'
LIMITS=dict(wall_seconds=60,no_progress_seconds=30,rss_bytes=512*1024**2,output_bytes=16*1024**2,files=64)


def require(value,message):
    if not value: raise ValueError(message)


def read(path): return json.loads(path.read_bytes())


def stamp(path):
    data=path.read_bytes()
    return dict(bytes=len(data),sha256=sha256(data).hexdigest())


def save(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')


def safe_directory(path):
    for p in reversed((path,*path.parents)):
        info=p.lstat()
        require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
            and not getattr(info,'st_file_attributes',0)&0x400,'nonordinary directory')


def create_output():
    require(Path.cwd().resolve()==ROOT.resolve(),'repository working directory required')
    safe_directory(BASE.parent)
    require(BASE.parent.resolve().is_relative_to(ROOT.resolve()),'output outside repository')
    BASE.mkdir(exist_ok=True)
    safe_directory(BASE)
    OUTPUT.mkdir()
    safe_directory(OUTPUT)
    require(OUTPUT.resolve().is_relative_to(ROOT.resolve()),'created output outside repository')


def check_p1(expected):
    safe_directory(P1)
    paths={}
    for directory,names,leaves in os.walk(P1,followlinks=False):
        for name in names+leaves:
            p=Path(directory)/name;info=p.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,'reparse input')
            require(stat.S_ISDIR(info.st_mode) if name in names else stat.S_ISREG(info.st_mode),'nonordinary input')
            if name in leaves:paths[p.relative_to(P1).as_posix()]=p
    require(set(paths)==set(expected),'saved P1 file set differs')
    require(all(not p.is_symlink() and stamp(p)==expected[n] for n,p in paths.items()),'saved P1 bytes differ')


def profile_inventory():
    safe_directory(OUTPUT)
    required={'start.json','worker.stdout.log','worker.stderr.log','events.jsonl','observations.json','report.json',
        'fingerprints.prof','fingerprints_stats.json','reopen.prof','reopen_stats.json'}
    paths={p.name:p for p in OUTPUT.iterdir()}
    require(set(paths)==required,'profile output file set differs')
    for p in paths.values():
        info=p.lstat()
        require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
            and not getattr(info,'st_file_attributes',0)&0x400 and info.st_nlink==1,'nonordinary profile output')
    pins={n:stamp(p) for n,p in paths.items()}
    require(all(pins[label+'.prof']['bytes']>0 for label in ('fingerprints','reopen')),'empty profile')
    return pins


def validate_profile_stats(label,wall):
    value=read(OUTPUT/(label+'_stats.json'))
    require(set(value)=={'profiled_wall_seconds','function_count','top_self','top_cumulative','scope'}
        and type(value['profiled_wall_seconds']) in (int,float) and math.isfinite(value['profiled_wall_seconds'])
        and value['profiled_wall_seconds']==wall and type(value['function_count']) is int and value['function_count']>0
        and value['scope']=='one profiled call; cumulative times overlap; instrumentation changes timing','profile stats scope differs')
    for name in ('top_self','top_cumulative'):
        rows=value[name]
        require(type(rows) is list and len(rows)==min(80,value['function_count']),'profile stats row count differs')
        for row in rows:
            require(type(row) is dict and set(row)=={'file','line','function','primitive_calls','calls','self_seconds','cumulative_seconds'}
                and all(type(row[k]) is str for k in ('file','function'))
                and all(type(row[k]) is int and row[k]>=0 for k in ('line','primitive_calls','calls'))
                and all(type(row[k]) in (int,float) and math.isfinite(row[k]) and row[k]>=0 for k in ('self_seconds','cumulative_seconds')),'invalid profile stats row')


def adopt_terminal(source_sha,contract_sha):
    require(stamp(PRIOR)['sha256']==PRIOR_SHA,'saved postcheck changed after quiet')
    expected=read(PRIOR)['p1_files'];check_p1(expected)
    require(stamp(PRIOR)['sha256']==PRIOR_SHA and stamp(Path(__file__))['sha256']==source_sha
        and stamp(CONTRACT)['sha256']==contract_sha,'input/source changed after quiet')
    output_before=profile_inventory()
    report,observed=read(OUTPUT/'report.json'),read(OUTPUT/'observations.json')
    fixed=dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,resource_admission=False,
        source_sha=source_sha,contract_sha=contract_sha,saved_input_sha=PRIOR_SHA,
        saved_files_checked=len(expected),saved_bytes_checked=sum(p['bytes'] for p in expected.values()),
        science_metrics_match=True,P1_bytes_unchanged=True,solver_calls=0,new_models=0,
        instrumentation_scope='setup/import/checks outside the two profiles remain in Job wall; profiling is not a speed comparison',
        C_overall_performance_review_complete=False,full_139_executed=False,fx_temporal_backing=False)
    timings={'one_profiled_fingerprint_seconds','one_profiled_reopen_seconds'}
    require(set(report)==set(fixed)|timings and all(type(report[k]) is type(v) and report[k]==v for k,v in fixed.items()),'terminal report differs')
    require(all(type(report[k]) in (int,float) and math.isfinite(report[k]) and report[k]>=0 for k in timings),'invalid profile timing')
    validate_profile_stats('fingerprints',report['one_profiled_fingerprint_seconds'])
    validate_profile_stats('reopen',report['one_profiled_reopen_seconds'])
    prior_observed=read(P1/'fresh_observations.json')
    require(set(observed)==set(prior_observed) and observed['allow_native'] is False
        and all(observed[k]==prior_observed[k] for k in ('scope','missing_process_observations')),'terminal observation scope differs')
    counts=observed['counts']
    forbidden_labels={'native_call','native_model','pyomo_build','numeric_compile','cas_put','publication'}
    forbidden={'native_factory_requested','forbidden_factory_requests','explicit_compile','importer_recompile','publication_requested_bytes'}
    forbidden|={prefix+label+'_'+suffix for prefix in ('','replay/') for label in forbidden_labels for suffix in ('attempts','returned','raised')}
    require(set(counts)<=set(prior_observed['counts'])|forbidden
        and all(type(v) is int and v>=0 for v in counts.values()),'unknown or invalid observation count')
    require(all(counts.get(k,0)==0 for k in forbidden),'terminal forbidden counts')
    seconds=observed['inclusive_seconds']
    require(set(seconds)<=set(prior_observed['inclusive_seconds'])|forbidden_labels
        and all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in seconds.values())
        and all(seconds.get(k,0)==0 for k in forbidden_labels),'terminal inclusive timings differ')
    require(profile_inventory()==output_before,'profile output changed during adoption')
    return dict(P1_bytes_rechecked_after_quiet=True,source_sha=source_sha,contract_sha=contract_sha,output_pins=output_before,
        prior_sha=PRIOR_SHA,report_pin=stamp(OUTPUT/'report.json'),observations_pin=stamp(OUTPUT/'observations.json'))


def profiled(label,function):
    profiler=cProfile.Profile();started=time.perf_counter()
    result=profiler.runcall(function)
    seconds=time.perf_counter()-started
    profiler.create_stats()
    with (OUTPUT/(label+'.prof')).open('xb') as stream:marshal.dump(profiler.stats,stream)
    stats=pstats.Stats(profiler).stats
    rows=[dict(file=k[0],line=k[1],function=k[2],primitive_calls=v[0],calls=v[1],self_seconds=v[2],cumulative_seconds=v[3]) for k,v in stats.items()]
    save(OUTPUT/(label+'_stats.json'),dict(profiled_wall_seconds=seconds,function_count=len(rows),
         top_self=sorted(rows,key=lambda r:r['self_seconds'],reverse=True)[:80],
         top_cumulative=sorted(rows,key=lambda r:r['cumulative_seconds'],reverse=True)[:80],
         scope='one profiled call; cumulative times overlap; instrumentation changes timing'))
    return result,seconds


def worker(source_sha,contract_sha):
    require(stamp(Path(__file__))['sha256']==source_sha and stamp(CONTRACT)['sha256']==contract_sha,'diagnostic source changed')
    require(stamp(PRIOR)['sha256']==PRIOR_SHA,'saved postcheck changed')
    expected=read(PRIOR)['p1_files'];check_p1(expected)
    from experiments import staged_rts24_native_probe_v1 as probe
    from src import staged_rts24_journal_v2 as journal,staged_rts24_development_v1 as c
    observations=probe.install_observers(allow_native=False)
    started=time.perf_counter()
    def event(stage):
        with (OUTPUT/'events.jsonl').open('ab') as stream:
            stream.write((json.dumps(dict(stage=stage,elapsed=time.perf_counter()-started))+'\n').encode())
    event('fingerprints_started')
    pins,fingerprint_wall=profiled('fingerprints',probe.fingerprints)
    require(pins==read(P1/'start.json')['pins'],'saved runtime dependency differs')
    event('fingerprints_returned')
    fixture=c.load_fixture();binding=read(P1/'trusted_binding.json')
    result,replay_wall=profiled('reopen',lambda:journal.reopen(P1/'journal',fixture,'on_time','early','full_temporal',binding))
    event('reopen_returned')
    require(probe.metrics(result)==read(P1/'fresh.json')['metrics'],'saved full scientific replay differs')
    require(probe.fingerprints()==pins,'runtime changed during diagnostic')
    check_p1(expected)
    require(stamp(Path(__file__))['sha256']==source_sha and stamp(CONTRACT)['sha256']==contract_sha,'diagnostic source changed after replay')
    observed=observations();counts=observed['counts']
    require(all(counts.get(k,0)==0 for k in ('native_factory_requested','native_call_attempts','native_model_attempts','pyomo_build_attempts','numeric_compile_attempts','forbidden_factory_requests')),'unexpected model or solver path')
    require(all(counts.get('replay/'+k+'_attempts',0)==0 for k in ('cas_put','publication')),'new evidence during replay')
    save(OUTPUT/'observations.json',observed)
    save(OUTPUT/'report.json',dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,resource_admission=False,
        source_sha=source_sha,contract_sha=contract_sha,saved_input_sha=PRIOR_SHA,
        saved_files_checked=len(expected),saved_bytes_checked=sum(p['bytes'] for p in expected.values()),
        one_profiled_fingerprint_seconds=fingerprint_wall,one_profiled_reopen_seconds=replay_wall,
        science_metrics_match=True,P1_bytes_unchanged=True,solver_calls=0,new_models=0,
        instrumentation_scope='setup/import/checks outside the two profiles remain in Job wall; profiling is not a speed comparison',
        C_overall_performance_review_complete=False,full_139_executed=False,fx_temporal_backing=False))
    event('complete')
    return 0


def launch():
    require(stamp(PRIOR)['sha256']==PRIOR_SHA,'saved postcheck changed')
    from src.staged_rts24_process_guard_v1 import supervise,controlled_environment
    from src import staged_rts24_development_v1 as c
    require(c.digest(controlled_environment())==read(P1/'start.json')['pins']['controlled_environment_sha'],'controlled environment differs')
    source_sha=stamp(Path(__file__))['sha256'];contract_sha=stamp(CONTRACT)['sha256']
    create_output()
    argv=[sys.executable,'-B','-s',str(Path(__file__).resolve()),'--worker','--source-sha',source_sha,'--contract-sha',contract_sha]
    save(OUTPUT/'start.json',dict(authority='DRAFT_NONAUTHORITATIVE',argv=argv,limits=LIMITS,
        source=stamp(Path(__file__)),contract=stamp(CONTRACT),saved_postcheck=stamp(PRIOR),native_authorized=False))
    record=supervise(argv,cwd=ROOT,output=OUTPUT,progress=OUTPUT/'events.jsonl',limits=LIMITS)
    accepted=record['exit_code']==0 and record['job_quiet_confirmed'] and record['stop_reason'] is None
    try:
        require(record['job_quiet_confirmed'],'diagnostic process not quiet')
        save(OUTPUT/'postquiet.json',adopt_terminal(source_sha,contract_sha))
    except BaseException as exc:
        save(OUTPUT/'adoption_failure.json',dict(type=type(exc).__name__,message=str(exc),accepted_success=False))
        accepted=False
    save(OUTPUT/'launcher.json',record)
    return 0 if accepted else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--worker',action='store_true')
    parser.add_argument('--source-sha');parser.add_argument('--contract-sha');args=parser.parse_args()
    if args.worker:
        require(OUTPUT.is_dir(),'profile output missing')
        with (OUTPUT/'worker.stdout.log').open('x',encoding='utf-8') as out,(OUTPUT/'worker.stderr.log').open('x',encoding='utf-8') as err:
            from contextlib import redirect_stdout,redirect_stderr
            with redirect_stdout(out),redirect_stderr(err):
                try:code=worker(args.source_sha,args.contract_sha)
                except BaseException as exc:
                    import traceback;traceback.print_exc();traceback.print_exc(file=err)
                    save(OUTPUT/'failure.json',dict(type=type(exc).__name__,message=str(exc),accepted_success=False));code=2
        sys.exit(code)
    sys.exit(launch())
