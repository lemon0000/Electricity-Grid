"""Create-only P2 metadata packet. There is deliberately no execution command."""
import argparse
from pathlib import Path
import sys
import time
import stat
import types

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    if Path.cwd().resolve()!=ROOT or any(n.split('.')[0] in ('src','experiments') for n in sys.modules):
        raise ValueError('fresh repository CLI scope required')
sys.path.insert(0,str(ROOT))
from experiments import staged_rts24_saved_profile_v1 as support
from experiments import staged_rts24_native_probe_v1 as p1
from src import staged_rts24_p2_packet_v1 as prep
from src import staged_rts24_journal_v2 as journal
from src import staged_rts24_shadow_runtime_v2 as identity

BASE=ROOT/'results/tables/staged_rts24_p2_packet_v1_non_authoritative'
OUTPUT=BASE/'packet_01'
PROPOSED_EXECUTION=ROOT/'results/tables/staged_rts24_p2_native_v1_non_authoritative/p2_01'
CONTRACT='docs/plan/staged_deliverability_c_p2_preparation_contract_v1.md'
read,save,stamp,require=support.read,support.save,support.stamp,support.require


def declared_sources():
    return frozenset(set(p1.SOURCES)|set(journal.SOURCE_PATHS)|{
        name.replace('.','/')+('/__init__.py' if name in identity.PACKAGES else '.py') for name in identity.APP_NAMES}|{
        'src/staged_rts24_p2_packet_v1.py','experiments/staged_rts24_p2_prepare_v1.py',
        'tests/test_staged_rts24_p2_packet_v1.py','tests/test_staged_rts24_p2_prepare_v1.py',
        'docs/plan/staged_deliverability_c_p2_preparation_contract_v1.md',
        'docs/plan/staged_deliverability_c_candidate_integration_cost_decision_v1.md'})


SOURCES=declared_sources()


def source_pins():return {name:stamp(ROOT/name) for name in sorted(SOURCES)}


def runtime_snapshot():
    identity.base.require(support is identity.support and p1 is identity.probe and prep.c is identity.core
        and journal is identity.journal and read is support.read and save is support.save and stamp is support.stamp
        and require is support.require and Path is identity.base.Path and sys is identity.base.sys
        and types is identity.base.types and stat is sys.modules['stat'],'preparation dependency alias differs')
    require(ROOT==identity.ROOT and BASE==ROOT/'results/tables/staged_rts24_p2_packet_v1_non_authoritative'
        and OUTPUT==BASE/'packet_01' and PROPOSED_EXECUTION==ROOT/'results/tables/staged_rts24_p2_native_v1_non_authoritative/p2_01',
        'preparation directory scope differs')
    require(type(SOURCES) is frozenset and SOURCES==declared_sources(),'preparation source set differs')
    require(CONTRACT=='docs/plan/staged_deliverability_c_p2_preparation_contract_v1.md','preparation contract differs')
    pins,refs=identity.snapshot()
    own={prep.__name__:ROOT/'src/staged_rts24_p2_packet_v1.py',__name__:ROOT/'experiments/staged_rts24_p2_prepare_v1.py'}
    require(__name__ in ('__main__','experiments.staged_rts24_p2_prepare_v1'),'noncanonical driver name')
    compiled={}
    for name,path in own.items():
        module=sys.modules.get(name)
        require(type(module) is types.ModuleType and module.__name__==name and Path(module.__file__).resolve()==path,'preparation module shadow')
        if name=='__main__':require(Path(sys.argv[0]).resolve()==path and sys.argv[1:]==['--prepare'],'preparation argv differs')
        else:
            spec=module.__spec__;parent,member=name.rsplit('.',1)
            require(spec is not None and spec.name==name and Path(spec.origin).resolve()==path
                and spec.submodule_search_locations is None and getattr(sys.modules.get(parent),member,None) is module,'preparation spec/parent differs')
        pins['application_modules'][name]=dict(path=str(path),pin=stamp(path));refs['application/'+name]=module
        for key,fn in tuple(vars(module).items()):
            if type(fn) is types.FunctionType and fn.__module__==name:
                label='preparation/'+name+'/'+key
                pins['functions'][label]=identity.base._function_pin(fn,compiled,pins['application_modules'])
                refs['function/'+label]=fn;refs['code/'+label]=fn.__code__
    require(vars(sys.modules[__name__]) is globals() and sys.modules.get(prep.__name__) is prep,'captured preparation module differs')
    pins['preparation_sources']=sorted(SOURCES)
    return pins,refs


def runtime_unchanged(before,refs):
    after,current=runtime_snapshot()
    require(after==before and set(current)==set(refs) and all(current[k] is v for k,v in refs.items()),'preparation runtime changed')
    return after


def module_inventory():return dict(sys.modules)


def check_module_inventory(before,allowed_added=()):
    after=module_inventory()
    require(all(name in after and after[name] is module for name,module in before.items())
        and set(after)-set(before)==set(allowed_added),'preparation loaded module inventory changed')
    return after


def check_inputs():
    require(stamp(support.PRIOR)['sha256']==support.PRIOR_SHA,'P1 anchor changed')
    support.check_p1(read(support.PRIOR)['p1_files'])
    require(not PROPOSED_EXECUTION.exists(),'proposed P2 execution directory already exists')


def cost_basis():
    prior=read(support.PRIOR);points=sorted((support.P1/'points').iterdir())
    files=[[p for p in point.rglob('*') if p.is_file()] for point in points]
    return dict(P1_command_seconds=prior['command_return']['command_outer_seconds'],P1_Job_seconds=prior['launcher']['outer_seconds'],
        point_processes=len(points),point_process_wall_seconds=sum(read(point/'process.json')['outer_seconds'] for point in points),
        native_internal_run_seconds=prior['native_run_seconds_sum'],fresh_seconds=prior['fresh_outer_seconds'],
        point_files=sum(len(group) for group in files),point_bytes=sum(p.stat().st_size for group in files for p in group),
        max_observed_files_per_point=max(map(len,files)),max_observed_bytes_per_point=max(sum(p.stat().st_size for p in group) for group in files),
        scope='saved P1 observations; overlapping stages not additive; no P2 timing forecast')


def inventory():
    support.safe_directory(OUTPUT);paths={p.name:p for p in OUTPUT.iterdir()}
    require(set(paths)=={'packet.json','context.json','observation.json'},'preparation file set differs')
    for path in paths.values():
        info=path.lstat()
        require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
            and not getattr(info,'st_file_attributes',0)&0x400 and info.st_nlink==1,'nonordinary preparation file')
    return {n:stamp(p) for n,p in paths.items()}


def prepare():
    require(sys.flags.no_user_site and sys.dont_write_bytecode,'controlled -B -s required')
    bootstrap,bootstrap_refs=runtime_snapshot();bootstrap_modules=module_inventory()
    p1.require_compute();check_inputs()
    pins=p1.fingerprints();preserved=p1.preserve();prior=read(support.P1/'start.json')
    require(pins==prior['pins'] and preserved==prior['preserved'],'original implementation or preserved inputs differ')
    sources=source_pins();fixture=prep.c.load_fixture();cost=cost_basis()
    runtime,refs=runtime_snapshot()
    require({k:v for k,v in bootstrap.items() if k!='stdlib'}=={k:v for k,v in runtime.items() if k!='stdlib'}
        and all(refs.get(k) is v for k,v in bootstrap_refs.items())
        and all(runtime.get('stdlib',{}).get(k)==v for k,v in bootstrap.get('stdlib',{}).items()),'metadata warmup changed existing bindings')
    warmup_added=sorted(set(runtime.get('stdlib',{}))-set(bootstrap.get('stdlib',{})))
    warmed_modules=check_module_inventory(bootstrap_modules,warmup_added)
    value=prep.packet(fixture)
    support.safe_directory(BASE.parent);BASE.mkdir(exist_ok=True);support.safe_directory(BASE)
    OUTPUT.mkdir()
    try:
        support.safe_directory(OUTPUT)
        require(OUTPUT.resolve().is_relative_to(ROOT.resolve()),'packet output outside repository')
        save(OUTPUT/'packet.json',value)
        context=dict(authority='DRAFT_NONAUTHORITATIVE',source_pins=sources,original_runtime_bindings=pins,preparation_runtime=runtime,
            metadata_warmup_added_stdlib=warmup_added,loaded_module_names=sorted(warmed_modules),
            P1_postcheck_pin=stamp(support.PRIOR),P1_cost_basis=cost,proposed_execution_directory=str(PROPOSED_EXECUTION),
            preparation_only=True,native_authorized=False,execution_supported=False,resource_admission=False)
        save(OUTPUT/'context.json',context)
        check_inputs()
        require(p1.fingerprints()==pins and p1.preserve()==preserved and source_pins()==sources,'preparation inputs changed')
        require(read(OUTPUT/'packet.json')==value,'saved packet differs')
        prep.validate_packet(read(OUTPUT/'packet.json'),fixture)
        observation=dict(authority='DRAFT_NONAUTHORITATIVE',preparation_completed=True,
            packet_pin=stamp(OUTPUT/'packet.json'),context_pin=stamp(OUTPUT/'context.json'),
            P1_files_rechecked=683,proposed_execution_directory_absent=True,native_authorized=False,
            execution_supported=False,resource_admission=False,scope='mechanical metadata preparation, no P2 execution or resource admission')
        save(OUTPUT/'observation.json',observation)
        before=inventory()
        require(prep.digest(read(OUTPUT/'context.json'))==prep.digest(context)
            and prep.digest(read(OUTPUT/'observation.json'))==prep.digest(observation),'preparation context/observation differs')
        require(before['packet.json']==observation['packet_pin'] and before['context.json']==observation['context_pin'],'preparation saved pins differ')
        runtime_unchanged(runtime,refs);check_inputs()
        check_module_inventory(warmed_modules)
        require(source_pins()==sources and inventory()==before,'preparation final bytes changed')
    except BaseException as exc:
        try:save(OUTPUT/'failure.json',dict(type=type(exc).__name__,message=str(exc),preparation_completed=False))
        except BaseException:pass
        raise
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true',required=True)
    parser.parse_args()
    started=time.perf_counter()
    code=prepare()
    print(dict(exit_code=code,preparation_command_seconds=time.perf_counter()-started,execution_supported=False))
