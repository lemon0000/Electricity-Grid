"""Read-only saved synthetic arm profile, not live roster authentication."""
import cProfile
import hashlib
import importlib.util
import json
from pathlib import Path
import pstats
import sys
import time
import traceback

E=Path(__file__).resolve().parent
ROOT=E.parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]


def hashes(root):
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob('*')) if p.is_file()}


def save(path,value):
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)


def main():
    saved=Path(sys.argv[1]);out=E/sys.argv[2];out.mkdir(exist_ok=False)
    spec=importlib.util.spec_from_file_location('common_profile_fixture',E/'replay_saved_with_fixture_v1.py')
    fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
    from experiments import h1_selector_input_snapshot_development_v2 as snapshot
    common=snapshot.common.common
    mode=sys.argv[3] if len(sys.argv)>3 else 'successor'
    if mode not in ('legacy','successor'):raise ValueError('explicit orchestration mode required')
    profiling='--timing-only' not in sys.argv
    all_arms='--all-arms' in sys.argv
    if mode=='legacy':
        old_spec=importlib.util.spec_from_file_location('common_before_profile',E/'common_bundle_repair_01/common_before.py')
        common=importlib.util.module_from_spec(old_spec);old_spec.loader.exec_module(common)
    header=json.loads(next(saved.glob('nt_non_authoritative/common_owners_non_authoritative/*/header.json')).read_bytes())['declaration']
    base=saved/'test_complete_independent_N0_r0'
    packet=json.loads((base/'parent_non_authoritative/worker_non_authoritative/selector_snapshot.json').read_bytes())
    declaration=packet['declaration']
    manifest,binding,configuration=snapshot._declarations(declaration['manifest'],
        declaration['source_binding'],declaration['run_configuration'])
    report=header['initial_report'];arm=report['canonical_arm']
    schedule=[(round_,name) for round_ in range(2) for name in sorted(report['arm_audits'])] if all_arms else [(0,arm)]
    before=hashes(saved)
    paths=[Path(__file__),Path(common.__file__),Path(snapshot.__file__),
        Path(common.phase.__file__),Path(common.phase.source.__file__),
        Path(common.bootstrap.historical_verifier.__file__),
        Path(common.bootstrap.historical_verifier.witness.__file__),E/'replay_saved_with_fixture_v1.py']
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    save(out/'request.json',dict(saved_root=str(saved),saved_files_sha256=before,
        implementation_pins=pins,scope='saved arms, synthetic source seams, no live roster',
        schedule=schedule,mode=mode,profiling=profiling,formal_result=False))
    patch=None;error=None;active=False;prof=cProfile.Profile();start=time.perf_counter()
    def audit(event,args):
        if active and event=='open':
            path,mode,flags=args
            if isinstance(mode,str) and any(c in mode for c in 'wax+'):
                raise RuntimeError('profile attempted a write')
    sys.addaudithook(audit)
    try:
        patch=fixture.complete_fixture(fixture.saved.synthetic_source)(base)
        active=True
        if profiling:prof.enable()
        results=[];first={}
        for round_,name in schedule:
            reference=report['arm_audits'][name]['reference']
            result=common._arm(reference,binding.registry_identity,manifest)
            assert common.encode(result[1])==common.encode(report['common_scientific_payload'])
            audit=json.loads(common.encode(result[2]));expected=json.loads(common.encode(report['arm_audits'][name]))
            audit.pop('verification_execution',None)
            audit['exact_current_audit'].pop('implementation_identity')
            expected['exact_current_audit'].pop('implementation_identity')
            assert common.encode(audit)==common.encode(expected)
            if name in first:assert common.encode(first[name])==common.encode(result[2])
            else:first[name]=result[2]
            results.append(dict(round=round_,arm=name,audit=result[2]))
            print(json.dumps(dict(round=round_,arm=name,elapsed_seconds=time.perf_counter()-start)),flush=True)
        prof.disable();active=False
        save(out/'projection.json',result[1])
        save(out/'audits.json',results)
    except BaseException:error=traceback.format_exc()
    finally:
        prof.disable();active=False
        if patch is not None:patch.undo()
    stats=pstats.Stats(prof) if profiling else None
    if profiling:
        prof.dump_stats(str(out/'profile.pstats'))
        with (out/'profile.txt').open('x',encoding='utf-8') as stream:
            pstats.Stats(prof,stream=stream).sort_stats('cumulative').print_stats(80)
    counts=[dict(file=k[0],line=k[1],function=k[2],primitive_calls=v[0],calls=v[1],
        own_seconds=v[2],cumulative_seconds=v[3]) for k,v in (stats.stats.items() if stats else ())
        if k[2] in ('_arm','_historical','_joined','_replay_prefix','_context','_inspect','inspect','prepare','guarded')
        and ('h1_' in k[0])]
    stable=before==hashes(saved) and all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in pins.items())
    terminal=dict(exit_code=0 if error is None and stable else 1,error=error,
        elapsed_seconds=time.perf_counter()-start,files_unchanged=stable,
        counts=counts,real_native_calls=0,Jobs=0,formal_result=False,
        full_chain_passed=False,includes_profiler=profiling,mode=mode,schedule=schedule,
        isolated_speed_comparison=False)
    save(out/'terminal.json',terminal)
    print(json.dumps(terminal),flush=True)
    return terminal['exit_code']


if __name__=='__main__':sys.exit(main())
