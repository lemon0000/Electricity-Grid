"""One solver-free profile of unchanged P2 input checks, never a P2 execution."""
import argparse
import cProfile
from contextlib import redirect_stdout,redirect_stderr
import importlib
from hashlib import sha256
import json
import marshal
import math
from pathlib import Path
import pstats
import subprocess
import os
import stat
import sys
import time
import types

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    if Path.cwd().resolve()!=ROOT or any(n.split('.')[0] in ('src','experiments') for n in sys.modules):
        raise ValueError('fresh repository CLI scope required')
sys.path.insert(0,str(ROOT))
from experiments import staged_rts24_p2_native_probe_v1 as p2
from src import staged_rts24_shadow_runtime_v1 as identity
from src.staged_rts24_process_guard_v1 import supervise,controlled_environment

BASE=ROOT/'results/tables/staged_rts24_p2_input_cost_v1_non_authoritative'
OUTPUT=BASE/'measure_01'
CONTRACT='docs/plan/staged_deliverability_c_p2_input_cost_contract_v1.md'
ANCHOR=ROOT/'results/tables/staged_rts24_p2_runner_v1_non_authoritative/development_checks_01/units_03.exit.json'
ANCHOR_SHA='753ead4ee09ea0f6f874e8d09d44fb5a6219a799e4843e9c22e56c0fddf58245'
LIMITS=dict(wall_seconds=60,no_progress_seconds=30,rss_bytes=512*1024**2,output_bytes=16*1024**2,files=64)
LABELS=('fingerprints','packet','preserve')
REQUIRED={'start.json','events.jsonl','worker.stdout.log','worker.stderr.log','runtime_before.json','runtime_after.json',
    'observations.json','report.json'}|{label+suffix for label in LABELS for suffix in ('.prof','_stats.json')}
read,save,stamp,require=p2.saved.read,p2.saved.save,p2.saved.stamp,p2.saved.require


def digest(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def expected_values():
    require(stamp(ANCHOR)['sha256']==ANCHOR_SHA,'P2 development anchor changed')
    require(stamp(p2.saved.PRIOR)['sha256']==p2.saved.PRIOR_SHA,'P1 anchor changed')
    require({p.name:stamp(p) for p in p2.PACKET.iterdir()}==p2.PACKET_PINS,'preparation bytes changed')
    old=read(p2.saved.P1/'start.json');sources=read(p2.PACKET/'context.json')['source_pins']
    direct=read(ANCHOR)['source_pins']
    require(set(direct)==set(p2.SOURCES) and all(stamp(ROOT/n)==v for n,v in {**sources,**direct}.items()),'bound P2 source changed')
    return dict(fingerprints=dict(legacy_scientific_and_P1_runtime=old['pins'],preparation_sources=sources,
        P2_sources=direct,preparation_files=p2.PACKET_PINS),packet=read(p2.PACKET/'packet.json'),
        preserve=dict(original=old['preserved'],P1_anchor=stamp(p2.saved.PRIOR),P2_preparation=p2.PACKET_PINS))


def source_pins():
    expected=expected_values()['fingerprints']
    pins={**expected['preparation_sources'],**expected['P2_sources']}
    for name in (str(Path(__file__).resolve().relative_to(ROOT)).replace('\\','/'),
        'tests/test_staged_rts24_p2_input_cost_v1.py',CONTRACT,'docs/plan/staged_deliverability_c_p2_runner_cost_review_v1.md'):
        pins[name]=stamp(ROOT/name)
    return pins


def input_check():
    expected_values();p2.saved.check_p1(read(p2.saved.PRIOR)['p1_files'])
    require(not p2.OUTPUT.exists() and not p2.REGISTRATION.exists(),'P2 execution state already exists')


def warm_imports():
    from src import staged_rts24_journal_v2 as journal
    for name in journal.EXTERNAL_MODULES:importlib.import_module(name)
    for name in ('pyomo.repn.standard_repn','pyomo.core.expr.numeric_expr','pyomo.core.expr.numvalue',
        'pyomo.core.expr.relational_expr','pyomo.core.base.var','pyomo.core.base.constraint','pyomo.core.base.objective',
        'pyomo.contrib.appsi.solvers','email.parser','email.feedparser','pypower.case24_ieee_rts'):
        importlib.import_module(name)


def runtime_snapshot():
    require(sys.flags.no_user_site and sys.dont_write_bytecode,'controlled -B -s required')
    p2.p1.require_compute();sources=source_pins();apps={};refs={};compiled={}
    for name,module in tuple(sys.modules.items()):
        if name.split('.')[0] not in ('src','experiments') and name!=__name__:continue
        require(type(module) is types.ModuleType and module.__name__==name,'application module shadow')
        path=Path(module.__file__).resolve();relative=path.relative_to(ROOT).as_posix()
        require(relative in sources,'undeclared application module: '+name)
        if name=='__main__':
            require(path==ROOT/'experiments/staged_rts24_p2_input_cost_v1.py' and Path(sys.argv[0]).resolve()==path,'driver argv differs')
        else:
            spec=module.__spec__;logical=ROOT.joinpath(*name.split('.'))
            expected=logical/'__init__.py' if hasattr(module,'__path__') else logical.with_suffix('.py')
            require(spec is not None and spec.name==name and Path(spec.origin).resolve()==path==expected,'application spec/path differs')
            if '.' in name:
                parent,member=name.rsplit('.',1);require(getattr(sys.modules[parent],member,None) is module,'application parent differs')
        apps[name]=dict(path=str(path),pin=stamp(path));refs['module/'+name]=module
    require(p2 is sys.modules.get('experiments.staged_rts24_p2_native_probe_v1')
        and vars(sys.modules[__name__]) is globals(),'captured application alias differs')
    functions=dict(P2_fingerprints=p2.fingerprints,P2_packet=p2.load_packet,P2_preserve=p2.preserve,
        legacy_fingerprints=p2.p1.fingerprints,legacy_preserve=p2.p1.preserve,legacy_stamp=p2.p1.stamp,
        saved_check=p2.saved.check_p1,code_pin=identity._function_pin,profile_call=cProfile.Profile.runcall)
    functions.update({'driver/'+n:f for n,f in vars(sys.modules[__name__]).items()
        if type(f) is types.FunctionType and f.__module__==__name__})
    functions.update({'deny/'+n:getattr(Deny,n) for n in ('__init__','install','check','restore')})
    pins={n:identity._function_pin(f,compiled,apps) for n,f in functions.items()}
    for n,f in functions.items():refs['function/'+n]=f;refs['code/'+n]=f.__code__
    std={n:stamp(Path(sys.modules[n].__file__)) for n in ('cProfile','pstats','profile','json','email.parser','email.feedparser')}
    profiler=sys.modules['_lsprof']
    require(profiler.__spec__.origin=='built-in' and not hasattr(profiler,'__file__'),'unexpected profiler extension origin')
    std['_lsprof']=dict(origin='built-in',executable_bound=True)
    return dict(applications=apps,functions=pins,selected_profiler_stdlib=std,loaded_module_names=sorted(sys.modules),executable=stamp(Path(sys.executable)),
        controlled_environment_sha=digest(controlled_environment()),scope='selected loaded modules and source-code functions; not complete OS closure'),refs


def runtime_unchanged(before,refs,modules):
    after,current=runtime_snapshot()
    require(after==before and set(current)==set(refs) and all(current[n] is v for n,v in refs.items()),'diagnostic runtime changed')
    require(set(sys.modules)==set(modules) and all(sys.modules[n] is v for n,v in modules.items()),'loaded module inventory changed')
    return after


def forbidden_labels():
    seen=set();labels=[]
    for owner,name in deny_targets():
        original=getattr(owner,name)
        if id(original) not in seen:
            labels.append(getattr(owner,'__name__',type(owner).__name__)+'.'+name);seen.add(id(original))
    return sorted(labels)


def validate_start(start):
    fixed=dict(authority='DRAFT_NONAUTHORITATIVE',limits=LIMITS,fixed_target_calls={n:1 for n in LABELS},native_authorized=False)
    require(set(start)==set(fixed)|{'source_pins','forbidden_labels'}
        and digest({n:start[n] for n in fixed})==digest(fixed)
        and start['forbidden_labels']==forbidden_labels(),'diagnostic start scope differs')


def deny_targets():
    import highspy
    import pyomo.environ as pyo
    from src import staged_rts24_evidence_store_v1 as codec,staged_rts24_numeric_interface_v1 as numeric
    from src import staged_rts24_highs_backend_v1 as backend,staged_rts24_journal_v2 as journal
    from src import staged_rts24_reference_queries_v1 as reference
    targets=[(highspy,'Highs'),(pyo,'SolverFactory'),(sys.modules['pyomo.contrib.appsi.solvers'],'Highs'),(backend,'make_model'),(backend,'call_highs'),
        (numeric,'compile_problem'),(numeric,'import_snapshot'),(p2.prep.c,'build_point_model'),
        (p2.prep.c,'load_fixture'),(p2.prep.c,'hour_requests'),(reference,'reference_requests'),
        (p2.prep,'packet'),(p2.prep,'validate_packet'),(p2.prep,'validate_schedule'),
        (codec,'publish'),(codec.EvidenceStore,'put')]
    targets += [(journal,n) for n in ('create_session','begin_step','commit_step','finish','reopen')]
    targets += [(module,n) for module in (p2,p2.p1) for n in ('cli','worker','point_worker','fresh_worker','registration_record','verify_registration')]
    targets += [(sys.modules['src.staged_rts24_process_guard_v1'],'supervise')]
    import subprocess,os
    targets += [(subprocess,'Popen'),(subprocess,'run'),(os,'system'),(os,'startfile')]
    return targets


class Deny:
    def __init__(self):self.calls={};self.aliases=[]

    def install(self):
        targets=deny_targets()
        factories={}
        for owner,name in targets:
            original=getattr(owner,name);label=getattr(owner,'__name__',type(owner).__name__)+'.'+name
            if id(original) not in factories:
                self.calls[label]=0
                def denied(*a,_label=label,**kw):
                    self.calls[_label]+=1
                    raise RuntimeError('forbidden diagnostic call: '+_label)
                factories[id(original)]=(original,denied,label)
        # Cover imported module aliases as well as the explicit class methods.
        owners={id(m):m for m in [m for m in tuple(sys.modules.values()) if type(m) is types.ModuleType]
            +[owner for owner,name in targets]}
        for owner in owners.values():
            for name,value in tuple(vars(owner).items()):
                entry=factories.get(id(value))
                if entry is not None and value is entry[0]:
                    setattr(owner,name,entry[1]);self.aliases.append((owner,name,value,entry[1]))
        require(len(self.aliases)>=len(factories),'forbidden route not installed')

    def check(self):
        require(all(getattr(m,n,None) is guard for m,n,old,guard in self.aliases),'diagnostic guard detached')
        require(all(type(v) is int and v==0 for v in self.calls.values()),'forbidden diagnostic call occurred')

    def restore(self):
        drift=[]
        for m,n,old,guard in reversed(self.aliases):
            if getattr(m,n,None) is not guard:drift.append(n)
            setattr(m,n,old)
        require(not drift,'diagnostic guard changed before restoration')


def event(stage,**meta):
    with (OUTPUT/'events.jsonl').open('ab') as stream:
        stream.write((json.dumps(dict(stage=stage,**meta))+'\n').encode());stream.flush()


def target_functions():
    return {'fingerprints':p2.fingerprints,'packet':p2.load_packet,'preserve':p2.preserve}


def target_identity(function):
    return dict(file=function.__code__.co_filename,line=function.__code__.co_firstlineno,name=function.__name__)


def profiled(label,function,**kwargs):
    profiler=cProfile.Profile();started=time.perf_counter()
    result=profiler.runcall(function,**kwargs)
    wall=time.perf_counter()-started;profiler.create_stats()
    with (OUTPUT/(label+'.prof')).open('xb') as stream:marshal.dump(profiler.stats,stream)
    stats=profiler.stats
    target=target_identity(function)
    summary=profile_summary(stats,target)
    require(summary['target_calls']==1 and summary['target_primitive_calls']==1,'profile target count differs')
    save(OUTPUT/(label+'_stats.json'),dict(summary,profiled_wall_seconds=wall,target=target,
        scope='one profiled original call; inclusive times overlap; warm imports and instrumentation'))
    return result,wall


def profile_summary(stats,target):
    require(type(stats) is dict and stats,'empty profile')
    rows=[dict(file=k[0],line=k[1],function=k[2],primitive_calls=v[0],calls=v[1],self_seconds=v[2],cumulative_seconds=v[3]) for k,v in stats.items()]
    require(all(type(r['file']) is type(r['function']) is str and type(r['line']) is int and r['line']>=0
        and all(type(r[k]) is int and r[k]>=0 for k in ('primitive_calls','calls'))
        and all(type(r[k]) in (int,float) and math.isfinite(r[k]) and r[k]>=0 for k in ('self_seconds','cumulative_seconds')) for r in rows),'invalid profile rows')
    row=stats.get((target['file'],target['line'],target['name']))
    require(row is not None,'profile target missing')
    return dict(function_count=len(rows),target_primitive_calls=row[0],target_calls=row[1],
        top_self=sorted(rows,key=lambda r:r['self_seconds'],reverse=True)[:80],
        top_cumulative=sorted(rows,key=lambda r:r['cumulative_seconds'],reverse=True)[:80])


def worker(start_sha):
    require(stamp(OUTPUT/'start.json')['sha256']==start_sha,'start changed')
    start=read(OUTPUT/'start.json');warm_imports();validate_start(start);input_check()
    require(source_pins()==start['source_pins'],'worker sources differ')
    expected=expected_values();runtime,refs=runtime_snapshot();modules=dict(sys.modules)
    require(runtime['loaded_module_names']==sorted(modules),'runtime module inventory differs')
    with (OUTPUT/'events.jsonl').open('xb'):pass
    save(OUTPUT/'runtime_before.json',runtime);event('inputs_checked')
    guard=Deny();timings={};results={}
    try:
        guard.install()
        require(sorted(guard.calls)==start['forbidden_labels'],'guard plan differs')
        functions=target_functions()
        for label in LABELS:
            event('profile_started',label=label)
            value,timings[label]=profiled(label,functions[label],**({'validate':False} if label=='packet' else {}))
            require(digest(value)==digest(expected[label]),'profiled result differs: '+label)
            results[label]=digest(value);event('profile_returned',label=label)
        guard.check()
    finally:
        if sys.exc_info()[0] is None:guard.restore()
        else:
            try:guard.restore()
            except BaseException as cleanup:
                try:save(OUTPUT/'guard_cleanup_failure.json',dict(type=type(cleanup).__name__,message=str(cleanup)))
                except BaseException:pass
    after=runtime_unchanged(runtime,refs,modules);input_check()
    require(source_pins()==start['source_pins'] and stamp(OUTPUT/'start.json')['sha256']==start_sha,'final source/start changed')
    save(OUTPUT/'runtime_after.json',after)
    save(OUTPUT/'observations.json',dict(target_calls={n:1 for n in LABELS},forbidden_calls=guard.calls,guards_restored=True,
        module_inventory_unchanged=True,loaded_module_names=sorted(modules),result_shas=results))
    save(OUTPUT/'report.json',dict(authority='DRAFT_NONAUTHORITATIVE',profiled_seconds=timings,result_shas=results,
        source_pins_sha=digest(start['source_pins']),runtime_sha=digest(runtime),P1_files_unchanged=683,
        solver_calls=0,new_models=0,new_replays=0,native_authorized=False,formal_result=False,resource_admission=False,
        C_overall_performance_review_complete=False,scope='three original input checks once each; no P2 execution or speedup'))
    event('complete');return 0


def inventory():
    p2.saved.safe_directory(OUTPUT);paths={p.name:p for p in OUTPUT.iterdir()}
    require(set(paths)==REQUIRED,'diagnostic file set differs')
    for p in paths.values():
        info=p.lstat();require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
            and not getattr(info,'st_file_attributes',0)&0x400 and info.st_nlink==1,'nonordinary diagnostic file')
    return {n:stamp(p) for n,p in paths.items()}


def adopt(start,start_sha):
    validate_start(start);input_check();require(source_pins()==start['source_pins'] and stamp(OUTPUT/'start.json')['sha256']==start_sha,'postquiet inputs changed')
    before=inventory();report=read(OUTPUT/'report.json');observed=read(OUTPUT/'observations.json')
    runtime=read(OUTPUT/'runtime_before.json')
    require(before['runtime_before.json']==before['runtime_after.json'],'runtime bookends differ')
    current,_=runtime_snapshot()
    require(current==runtime,'parent/worker selected runtime differs')
    names=observed['loaded_module_names']
    require(type(names) is list and all(type(n) is str for n in names) and names==sorted(set(names))
        and names==runtime['loaded_module_names'],'saved module inventory differs')
    events=[json.loads(line) for line in (OUTPUT/'events.jsonl').read_bytes().splitlines()]
    expected_events=[dict(stage='inputs_checked')]
    for label in LABELS:expected_events.extend((dict(stage='profile_started',label=label),dict(stage='profile_returned',label=label)))
    expected_events.append(dict(stage='complete'))
    require(events==expected_events,'saved diagnostic event sequence differs')
    require(set(observed)=={'target_calls','forbidden_calls','guards_restored','module_inventory_unchanged','loaded_module_names','result_shas'}
        and set(observed['target_calls'])==set(LABELS) and all(type(v) is int and v==1 for v in observed['target_calls'].values())
        and sorted(observed['forbidden_calls'])==start['forbidden_labels']
        and all(type(v) is int and v==0 for v in observed['forbidden_calls'].values())
        and observed['guards_restored'] is True and observed['module_inventory_unchanged'] is True,'observation incomplete')
    expected=expected_values();shas={n:digest(v) for n,v in expected.items()}
    fixed=dict(authority='DRAFT_NONAUTHORITATIVE',result_shas=shas,source_pins_sha=digest(start['source_pins']),runtime_sha=digest(runtime),
        P1_files_unchanged=683,solver_calls=0,new_models=0,new_replays=0,native_authorized=False,formal_result=False,
        resource_admission=False,C_overall_performance_review_complete=False,
        scope='three original input checks once each; no P2 execution or speedup')
    require(set(report)==set(fixed)|{'profiled_seconds'} and digest({n:report[n] for n in fixed})==digest(fixed)
        and observed['result_shas']==shas,'result/source/runtime adoption differs')
    require(set(report['profiled_seconds'])==set(LABELS),'profile phase set differs')
    for label in LABELS:
        stats=read(OUTPUT/(label+'_stats.json'));wall=report['profiled_seconds'][label]
        require(type(wall) in (int,float) and math.isfinite(wall) and wall>=0 and stats['profiled_wall_seconds']==wall
            and type(stats['function_count']) is int and stats['function_count']>0 and before[label+'.prof']['bytes']>0,'profile incomplete')
        require(set(stats)=={'profiled_wall_seconds','function_count','target_calls','target_primitive_calls','top_self','top_cumulative','target','scope'},'profile schema differs')
        require(stats['target']==target_identity(target_functions()[label]),'profile target identity differs')
        with (OUTPUT/(label+'.prof')).open('rb') as stream:
            data=marshal.load(stream);require(stream.read()==b'','profile trailing bytes')
        require(profile_summary(data,stats['target'])=={n:stats[n] for n in ('function_count','target_calls','target_primitive_calls','top_self','top_cumulative')}
            and stats['target_calls']==stats['target_primitive_calls']==1,'profile data/summary differs')
    require(inventory()==before,'diagnostic output changed during adoption')
    return dict(output_pins=before,source_pins_sha=digest(start['source_pins']),P1_rechecked_after_quiet=True)


def launch():
    p2.p1.require_compute();warm_imports();input_check()
    require(digest(controlled_environment())==read(p2.saved.P1/'start.json')['pins']['controlled_environment_sha'],'controlled environment differs')
    sources=source_pins();p2.saved.safe_directory(BASE.parent);BASE.mkdir(exist_ok=True);p2.saved.safe_directory(BASE)
    OUTPUT.mkdir();p2.saved.safe_directory(OUTPUT)
    argv=[sys.executable,'-B','-s',str(Path(__file__).resolve()),'--worker']
    start=dict(authority='DRAFT_NONAUTHORITATIVE',source_pins=sources,limits=LIMITS,
        fixed_target_calls={n:1 for n in LABELS},forbidden_labels=forbidden_labels(),native_authorized=False)
    save(OUTPUT/'start.json',start);start_sha=stamp(OUTPUT/'start.json')['sha256']
    record=supervise(argv+['--start-sha',start_sha],cwd=ROOT,output=OUTPUT,progress=OUTPUT/'events.jsonl',limits=LIMITS)
    accepted=record['exit_code']==0 and record['stop_reason'] is None and record['job_quiet_confirmed']
    try:
        require(accepted,'diagnostic process did not finish quiet successfully')
        save(OUTPUT/'postquiet.json',adopt(start,start_sha))
    except BaseException as exc:
        save(OUTPUT/'adoption_failure.json',dict(type=type(exc).__name__,message=str(exc),accepted_success=False));accepted=False
    save(OUTPUT/'launcher.json',record);return 0 if accepted else 1


def cli():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--worker',action='store_true')
    parser.add_argument('--start-sha');args=parser.parse_args()
    if not args.worker:return launch()
    require(OUTPUT.is_dir(),'diagnostic output missing')
    with (OUTPUT/'worker.stdout.log').open('x',encoding='utf-8') as out,(OUTPUT/'worker.stderr.log').open('x',encoding='utf-8') as err:
        with redirect_stdout(out),redirect_stderr(err):
            try:return worker(args.start_sha)
            except BaseException as exc:
                import traceback;traceback.print_exc(file=err);err.flush()
                save(OUTPUT/'failure.json',dict(type=type(exc).__name__,message=str(exc),accepted_success=False));return 2


if __name__=='__main__':sys.exit(cli())
