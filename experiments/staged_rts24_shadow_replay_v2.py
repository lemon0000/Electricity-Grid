"""One fixed saved-P1 shadow attempt; never supplies a scientific decision."""
import argparse
from contextlib import redirect_stdout,redirect_stderr
from hashlib import sha256
import json
from pathlib import Path
import stat
import sys
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiments import staged_rts24_saved_profile_v1 as support

BASE=ROOT/'results/tables/staged_rts24_shadow_replay_v2_non_authoritative'
OUTPUT=BASE/'shadow_01'
P1=support.P1
CONTRACT='docs/plan/staged_deliverability_c_shadow_replay_contract_v2.md'
LIMITS=dict(wall_seconds=60,no_progress_seconds=30,rss_bytes=512*1024**2,output_bytes=16*1024**2,files=64)
STAGES=dict(reopen=1,replay_entry=6,prepare_hour=10,propose_hour=10,accept_hour=5,
    audit_execution=17,audit_child_lp=118,execution_summary=1)
EXPECTED=dict(digest_started=2547,parent_json_returns=2547,digest_returned=2547,strict_byte_compares=2547,json_returns=4861)
EXPECTED.update({name+'/'+kind:count for name,count in STAGES.items() for kind in ('started','returned')})
REQUIRED={'start.json','events.jsonl','worker.stdout.log','worker.stderr.log',
    'runtime_before.json','runtime_after.json','shadow.json','report.json'}

read,stamp,save,require=support.read,support.stamp,support.save,support.require


def digest(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def same(left,right):
    return json.dumps(left,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(right,sort_keys=True,separators=(',',':'),allow_nan=False)


def input_check():
    require(stamp(support.PRIOR)['sha256']==support.PRIOR_SHA,'P1 anchor changed')
    support.check_p1(read(support.PRIOR)['p1_files'])


def sources():
    from src.staged_rts24_shadow_runtime_v2 import probe,journal,APP_NAMES,PACKAGES
    paths=set(probe.SOURCES)|set(journal.SOURCE_PATHS)|{
        'src/staged_rts24_plain_v2.py','src/staged_rts24_shadow_monitor_v2.py','src/staged_rts24_shadow_runtime_v2.py',
        'experiments/staged_rts24_shadow_replay_v2.py','experiments/staged_rts24_saved_profile_v1.py',
        'tests/test_staged_rts24_plain_v2.py','tests/test_staged_rts24_shadow_monitor_v2.py','tests/test_staged_rts24_shadow_replay_v2.py',CONTRACT}
    paths.update(name.replace('.','/')+('/__init__.py' if name in PACKAGES else '.py') for name in APP_NAMES)
    return {name:stamp(ROOT/name) for name in sorted(paths)}


def prepare():
    from src import staged_rts24_shadow_runtime_v2 as runtime
    path=ROOT/'experiments/staged_rts24_shadow_replay_v2.py'
    module=sys.modules.get(__name__)
    require(module is not None and vars(module) is globals() and Path(__file__).resolve()==path
        and support is runtime.support,'driver module binding differs')
    if __name__=='__main__':require(Path(sys.argv[0]).resolve()==path,'driver argv path differs')
    else:
        require(__name__=='experiments.staged_rts24_shadow_replay_v2'
            and module.__spec__.name==__name__ and Path(module.__spec__.origin).resolve()==path,'driver import shadow')
    require(sys.flags.no_user_site and sys.dont_write_bytecode,'controlled -B -s invocation required')
    fixture=runtime.core.load_fixture();trusted=read(P1/'trusted_binding.json')
    pins=runtime.probe.fingerprints()
    require(pins==read(P1/'start.json')['pins'],'original P1 runtime differs')
    identity,refs=runtime.snapshot()
    return runtime,fixture,trusted,pins,identity,refs


def create_output():
    require(Path.cwd().resolve()==ROOT.resolve(),'repository cwd required')
    support.safe_directory(BASE.parent)
    require(BASE.parent.resolve().is_relative_to(ROOT.resolve()),'output outside repository')
    BASE.mkdir(exist_ok=True);support.safe_directory(BASE)
    OUTPUT.mkdir();support.safe_directory(OUTPUT)
    require(OUTPUT.resolve().is_relative_to(ROOT.resolve()),'created output outside repository')


def event(stage,**values):
    with (OUTPUT/'events.jsonl').open('ab') as stream:
        stream.write((json.dumps(dict(stage=stage,**values))+'\n').encode())


def expected_report(start):
    return dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,resource_admission=False,
        C_overall_performance_review_complete=False,full_139_executed=False,fx_temporal_backing=False,
        metrics=read(P1/'fresh.json')['metrics'],source_pins_sha=digest(start['source_pins']),
        runtime_pins_sha=digest(start['runtime']),legacy_pins_sha=digest(start['legacy_pins']),
        equivalent_digest_calls=2547,direct_alias_calls=118,other_digest_calls=2429,
        P1_files_unchanged=683,P1_bytes_unchanged=2950863,registered_forbidden_calls=0,
        scope='one_original_saved_P1_reopen_with_observational_shadow_not_candidate_execution_or_speedup')


def validate_shadow(value):
    require(set(value)=={'authority','counts','callers','pending','first_error','monitor_cleaned','scope'},'shadow schema differs')
    require(value['authority']=='DRAFT_NONAUTHORITATIVE' and value['counts']==EXPECTED
        and all(type(v) is int for v in value['counts'].values())
        and type(value['pending']) is int and value['pending']==0 and value['first_error'] is None and value['monitor_cleaned'] is True
        and value['scope']=='actual_legacy_JSON_bytes_and_digest_returns_not_CAS_blob_identity_or_speedup','shadow incomplete')
    callers=value['callers']
    require(type(callers) is dict and all(type(k) is str and type(v) is int and v>0 for k,v in callers.items())
        and sum(callers.values())==2547,'caller total differs')
    child=sum(v for k,v in callers.items() if k.split('|')[1]=='audit_child_lp'
        and Path(k.split('|')[0]).resolve()==(ROOT/'src/staged_rts24_child_optimality_v1.py').resolve())
    require(child==118 and sum(callers.values())-child==2429,'direct alias coverage differs')


def inventory():
    support.safe_directory(OUTPUT)
    paths={p.name:p for p in OUTPUT.iterdir()}
    require(set(paths)==REQUIRED,'shadow output file set differs')
    for p in paths.values():
        info=p.lstat()
        require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
            and not getattr(info,'st_file_attributes',0)&0x400 and info.st_nlink==1,'nonordinary shadow output')
    return {name:stamp(path) for name,path in paths.items()}


def adopt(start,start_pin):
    before=inventory();require(before['start.json']==start_pin,'start bytes changed')
    input_check();require(sources()==start['source_pins'],'shadow sources changed after quiet')
    require(same(read(OUTPUT/'runtime_before.json'),start['runtime']) and same(read(OUTPUT/'runtime_after.json'),start['runtime']),'saved runtime identity differs')
    validate_shadow(read(OUTPUT/'shadow.json'))
    require(same(read(OUTPUT/'report.json'),expected_report(start)),'shadow report differs')
    require((OUTPUT/'worker.stderr.log').read_bytes()==b'' and (OUTPUT/'worker.stdout.log').read_bytes()==b'','unexpected worker output')
    require(inventory()==before,'shadow output changed during adoption')
    return dict(authority='DRAFT_NONAUTHORITATIVE',P1_rechecked_after_quiet=True,source_pins_sha=digest(start['source_pins']),
        runtime_pins_sha=digest(start['runtime']),output_pins=before,formal_result=False,resource_admission=False)


def worker(start_sha):
    start=read(OUTPUT/'start.json')
    require(stamp(OUTPUT/'start.json')['sha256']==start_sha,'start SHA differs')
    input_check();require(sources()==start['source_pins'],'shadow source differs')
    event('inputs_checked')
    runtime,fixture,trusted,pins,identity,refs=prepare()
    require(same(identity,start['runtime']) and same(pins,start['legacy_pins']),'fresh runtime registration differs')
    save(OUTPUT/'runtime_before.json',identity)
    stages,forbidden=runtime.routes()
    mon=runtime.shadow.ShadowMonitor(stages,forbidden,EXPECTED,progress=lambda n:event('digest_progress',completed=n))
    event('reopen_started')
    try:
        with mon:result=runtime.journal.reopen(P1/'journal',fixture,'on_time','early','full_temporal',trusted)
    except BaseException:
        # Diagnostics cannot replace the original scientific/control exception.
        try:save(OUTPUT/'diagnostic.json',mon.summary())
        except BaseException:pass
        raise
    mon.require_complete();value=mon.summary();validate_shadow(value)
    require(runtime.probe.metrics(result)==read(P1/'fresh.json')['metrics'],'legacy full replay differs')
    require(runtime.probe.fingerprints()==pins,'original runtime changed')
    after=runtime.unchanged(identity,refs);input_check()
    require(sources()==start['source_pins'],'shadow source changed')
    save(OUTPUT/'runtime_after.json',after);save(OUTPUT/'shadow.json',value)
    save(OUTPUT/'report.json',expected_report(start));event('complete')
    return 0


def launch():
    input_check();runtime,fixture,trusted,pins,identity,refs=prepare()
    source_pins=sources();create_output()
    start=dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,resource_admission=False,native_authorized=False,
        source_pins=source_pins,runtime=identity,legacy_pins=pins,limits=LIMITS,expected_counts=EXPECTED,
        attempt_count=1,question='all_2547_actual_original_digest_calls_strict_bytes_and_SHA_equal',
        parent_preparation_and_postquiet_outside_Job_wall=True)
    save(OUTPUT/'start.json',start);start_pin=stamp(OUTPUT/'start.json')
    argv=[sys.executable,'-B','-s',str(Path(__file__).resolve()),'--worker','--start-sha',start_pin['sha256']]
    from src.staged_rts24_process_guard_v1 import supervise
    record=supervise(argv,cwd=ROOT,output=OUTPUT,progress=OUTPUT/'events.jsonl',limits=LIMITS)
    record['argv']=argv
    accepted=record['exit_code']==0 and record['stop_reason'] is None and record['job_quiet_confirmed']
    try:
        require(accepted,'shadow process was not successful (see launcher exit, stop and quiet fields)')
        require(same(runtime.unchanged(identity,refs),start['runtime']),'parent runtime changed after quiet')
        save(OUTPUT/'postquiet.json',adopt(start,start_pin))
    except BaseException as exc:
        save(OUTPUT/'adoption_failure.json',dict(type=type(exc).__name__,message=str(exc),accepted_success=False));accepted=False
    save(OUTPUT/'launcher.json',record)
    return 0 if accepted else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--worker',action='store_true')
    parser.add_argument('--start-sha');args=parser.parse_args()
    if args.worker:
        require(OUTPUT.is_dir(),'shadow output missing')
        with (OUTPUT/'worker.stdout.log').open('x',encoding='utf-8') as out,(OUTPUT/'worker.stderr.log').open('x',encoding='utf-8') as err:
            with redirect_stdout(out),redirect_stderr(err):
                try:code=worker(args.start_sha)
                except BaseException as exc:
                    traceback.print_exc();traceback.print_exc(file=err)
                    save(OUTPUT/'failure.json',dict(type=type(exc).__name__,message=str(exc),accepted_success=False,scientific_outcome='unresolved'));code=2
        sys.exit(code)
    sys.exit(launch())
