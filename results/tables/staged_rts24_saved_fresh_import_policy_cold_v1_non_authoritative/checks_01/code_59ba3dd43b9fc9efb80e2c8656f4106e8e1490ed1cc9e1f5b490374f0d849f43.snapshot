"""Bounded Windows transport correction; reuse the frozen 41-node source epoch."""
import time
STARTED=time.perf_counter()
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;ROOT=BASE.parents[2];PACKAGE=BASE/'final_package_01'
V1=ROOT/'results/tables/staged_rts24_saved_fresh_import_policy_v1_non_authoritative'
V2=ROOT/'results/tables/staged_rts24_saved_fresh_import_policy_v2_non_authoritative'
WIRE=ROOT/'results/tables/staged_rts24_saved_fresh_wire_data_v1_non_authoritative'
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
BASELINE_RAW=(OUT/'baseline.json').read_bytes();baseline=json.loads(BASELINE_RAW)
ancestor=read(V2/'checks_01/baseline.json')
old=WIRE/'checks_01/run.py';assert pin(old.read_bytes())==ancestor['preserved'][old.relative_to(ROOT).as_posix()]
spec=importlib.util.spec_from_file_location('bounded_transport_capture',old);capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
def sources():return names(ROOT/n for n in baseline['source_pins'])
def helpers():return names(p for d in (OUT,PACKAGE) for p in d.glob('*.py'))
def fixed():
    assert names(ROOT/n for n in baseline['preserved'])==baseline['preserved']
    assert names(ROOT/n for n in ancestor['preserved'])==ancestor['preserved']
    assert len(set(baseline['preserved'])|set(ancestor['preserved']))==baseline['preserved_paths']==4616
    return pin(raw(dict(ancestor=ancestor['preserved'],successor=baseline['preserved'])))
def snapshot(data):
    for d in (V2/'checks_01',V1/'checks_01',WIRE/'checks_02',WIRE/'checks_01',ROOT/'results/tables/staged_rts24_saved_fresh_role_data_v1_non_authoritative/checks_01',OUT):
        p=d/('code_'+sha256(data).hexdigest()+'.snapshot')
        if p.exists():assert p.read_bytes()==data;return
    with p.open('xb') as stream:stream.write(data)
def storage(reserve_files,reserve_bytes):
    def use(root):
        files=[p for p in root.rglob('*') if p.is_file()];return len(files),sum(p.stat().st_size for p in files)
    own=use(BASE);v1=use(V1);v2=use(V2)
    assert own[0]+reserve_files<=64 and own[1]+reserve_bytes<=4*1024**2
    assert own[0]+v1[0]+v2[0]+reserve_files<=128 and own[1]+v1[1]+v2[1]+reserve_bytes<=8*1024**2
def records():
    return {p.relative_to(ROOT).as_posix():read(p) for d in (WIRE/'checks_01',WIRE/'final_package_01',WIRE/'checks_02',WIRE/'final_package_02',V1/'checks_01',V2/'checks_01',V2/'final_package_01',OUT,PACKAGE) for p in d.glob('*.exit.json')}
if __name__=='__main__':
    action=sys.argv[1];assert action in baseline['phase_caps'];cap=baseline['phase_caps'][action]
    prior=records();spent={k:sum(r['charged_seconds'] for r in prior.values() if r['kind']==k) for k in ('static','pytest')}
    assert spent['static']+cap<=120 and spent['pytest']<=420 and sum(spent.values())+cap<=540
    target=OUT if action=='cold_import' else PACKAGE;script=OUT/'cold_import.py' if action=='cold_import' else PACKAGE/'oracle.py'
    for suffix in ('stdout.log','stderr.log','exit.json'):assert not (target/(action+'.'+suffix)).exists()
    before_source=sources();before_helpers=helpers();before_fixed=fixed()
    assert before_source==baseline['source_pins'] and before_helpers==baseline['helper_pins']
    controls={(OUT/'baseline.json').relative_to(ROOT).as_posix():pin(BASELINE_RAW)}
    assert names(ROOT/n for n in controls)==controls
    if action!='cold_import':
        anchor=read(OUT/'cold_import.exit.json');assert anchor['accepted'] and anchor['returncode']==0 and anchor['helper_pins']==before_helpers
        assert names(ROOT/n for n in anchor['child_artifact_pins'])==anchor['child_artifact_pins']
    for n in {*before_source,*before_helpers}:snapshot((ROOT/n).read_bytes())
    storage(12 if action=='cold_import' else 5 if action=='saved' else 4,500000)
    preparation=time.perf_counter()-STARTED;timeout=cap-3.-preparation;assert timeout>0
    argv=[sys.executable,'-B',str(script),action];started=time.perf_counter()
    code,stdout,stderr,error,state=capture.spawn_and_drain(argv,timeout);target_seconds=time.perf_counter()-started
    produced_names=[f'cold_{case}.{suffix}' for case in baseline['cold_cases'] for suffix in ('stdout.log','stderr.log','json')] if action=='cold_import' else ['checkpoint_freeze.json','saved_report.json'] if action=='saved' else ['terminal_report.json']
    produced_paths=[target/n for n in produced_names];missing=[p.relative_to(ROOT).as_posix() for p in produced_paths if not p.exists()]
    produced=names(p for p in produced_paths if p.exists());after_source=sources();after_helpers=helpers();after_fixed=fixed()
    after_controls=names(ROOT/n for n in controls)
    post_ok=before_source==after_source and before_helpers==after_helpers and before_fixed==after_fixed and controls==after_controls and not missing
    charged=time.perf_counter()-STARTED+.5
    value=dict(authority='DRAFT_NONAUTHORITATIVE',label=action,kind='static',argv=argv,returncode=code,error=error,
        accepted=code==0 and error is None and post_ok and charged<=cap,child_artifact_pins=produced,missing_child_artifacts=missing,
        source_pins=before_source,after_source_pins=after_source,helper_pins=before_helpers,after_helper_pins=after_helpers,
        controls_pins=controls,after_controls_pins=after_controls,postcheck_pins_match=post_ok,fixed_before=before_fixed,fixed_after=after_fixed,
        source_epoch=sha256(raw(before_source)).hexdigest(),stdout_pin=pin(stdout),stderr_pin=pin(stderr),bounded_drain=state,
        charged_seconds=charged,tail_reserve_seconds=.5,target_seconds=target_seconds,preparation_seconds=preparation,target_timeout_seconds=timeout,cap_seconds=cap,
        prior_record_pins={n:pin((ROOT/n).read_bytes()) for n in prior},previous_charged_seconds=spent,
        actual_F=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False,whole_workflow_wall_budget_verified=False,package_postcheck_verified=True)
    data=raw(value);storage(3,len(stdout)+len(stderr)+len(data))
    for suffix,payload in (('stdout.log',stdout),('stderr.log',stderr),('exit.json',data)):
        with (target/(action+'.'+suffix)).open('xb') as stream:stream.write(payload)
    print(json.dumps(dict(label=action,accepted=value['accepted'],returncode=code,charged_seconds=charged,cumulative_static_seconds=spent['static']+charged),sort_keys=True))
    if not value['accepted']:raise SystemExit(1)
