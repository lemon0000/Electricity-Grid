"""Continue the original cumulative budget; immutable predecessor captures remain bound."""
import time
STARTED=time.perf_counter()
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;ROOT=BASE.parents[2];PACKAGE=BASE/'final_package_02'
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
baseline=read(OUT/'continuation_baseline.json')
old=BASE/'checks_01/run.py';assert pin(old.read_bytes())==baseline['preserved'][old.relative_to(ROOT).as_posix()]
spec=importlib.util.spec_from_file_location('pinned_bounded_capture',old);capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
def sources():return names(ROOT/n for n in baseline['sources'])
def helpers():return names(p for d in (OUT,PACKAGE) for p in d.glob('*.py'))
def fixed():
    expected={**baseline['predecessor_preserved'],**baseline['preserved']}
    assert names(ROOT/n for n in expected)==expected,'historical exact bytes changed'
    actual=sources();assert all(actual[n]==p for n,p in baseline['sources'].items() if n not in (
        'experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py'))
    return pin(raw(expected))
def snapshot(data):
    for d in (BASE/'checks_01',ROOT/'results/tables/staged_rts24_saved_fresh_role_data_v1_non_authoritative/checks_01',OUT):
        p=d/('code_'+sha256(data).hexdigest()+'.snapshot')
        if p.exists():assert p.read_bytes()==data;return
    with p.open('xb') as stream:stream.write(data)
def storage(reserve_files,reserve_bytes):
    main=[p for d in (BASE/'checks_01',OUT) for p in d.rglob('*') if p.is_file()]
    package=[p for d in (BASE/'final_package_01',PACKAGE) for p in d.rglob('*') if p.is_file()]
    assert len(main)+(reserve_files if target==OUT else 0)<=180
    assert len(package)+(reserve_files if target==PACKAGE else 0)<=24
    assert sum(p.stat().st_size for p in main)+(reserve_bytes if target==OUT else 0)<=14*1024**2
    assert sum(p.stat().st_size for p in package)+(reserve_bytes if target==PACKAGE else 0)<=2*1024**2
    files=[p for p in BASE.rglob('*') if p.is_file()]
    assert len(files)+reserve_files<=204 and sum(p.stat().st_size for p in files)+reserve_bytes<=16*1024**2
if __name__=='__main__':
    action=sys.argv[1];assert action in baseline['phase_caps']
    cap=baseline['phase_caps'][action];kind='pytest' if action.startswith('pytest_') else 'static'
    target=OUT if action in ('collection','pytest_a','pytest_b') else PACKAGE
    script=OUT/'pytest_harness.py' if target==OUT else PACKAGE/'oracle.py'
    args=['--collect-only',action] if action=='collection' else ['admission.json',action] if kind=='pytest' else [action]
    records={p.relative_to(ROOT).as_posix():read(p) for d in (BASE/'checks_01',BASE/'final_package_01',OUT,PACKAGE) for p in d.glob('*.exit.json')}
    spent={k:sum(v['charged_seconds'] for v in records.values() if v['kind']==k) for k in ('static','pytest')}
    assert spent[kind]+cap<=(120 if kind=='static' else 420) and sum(spent.values())+cap<=540
    for suffix in ('stdout.log','stderr.log','exit.json'):assert not (target/(action+'.'+suffix)).exists()
    before_source=sources();before_helpers=helpers();before_fixed=fixed()
    for n in {*before_source,*before_helpers}:snapshot((ROOT/n).read_bytes())
    storage(6 if action=='collection' else 4,650000 if action=='collection' else 370000)
    preparation=time.perf_counter()-STARTED;timeout=cap-3.-preparation
    argv=[sys.executable,'-B',str(script),*args];started=time.perf_counter()
    if timeout<=0:raise RuntimeError('preparation exhausted; no child launched')
    code,stdout,stderr,error,state=capture.spawn_and_drain(argv,timeout)
    target_seconds=time.perf_counter()-started
    after_source=sources();after_helpers=helpers();after_fixed=fixed()
    post_ok=before_source==after_source and before_helpers==after_helpers and before_fixed==after_fixed
    charged=time.perf_counter()-STARTED+.5
    value=dict(authority='DRAFT_NONAUTHORITATIVE',label=action,kind=kind,argv=argv,returncode=code,error=error,
        accepted=code==0 and error is None and post_ok and charged<=cap,source_pins=before_source,helper_pins=before_helpers,
        after_source_pins=after_source,after_helper_pins=after_helpers,postcheck_pins_match=post_ok,
        fixed_before=before_fixed,fixed_after=after_fixed,source_epoch=sha256(raw(before_source)).hexdigest(),
        stdout_pin=pin(stdout),stderr_pin=pin(stderr),bounded_drain=state,charged_seconds=charged,tail_reserve_seconds=.5,
        target_seconds=target_seconds,preparation_seconds=preparation,target_timeout_seconds=timeout,cap_seconds=cap,
        prior_record_pins={n:pin((ROOT/n).read_bytes()) for n in records},previous_charged_seconds=spent,
        actual_F=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False,
        whole_workflow_wall_budget_verified=False,package_postcheck_verified=True)
    data=raw(value);storage(3,len(stdout)+len(stderr)+len(data))
    for suffix,payload in (('stdout.log',stdout),('stderr.log',stderr),('exit.json',data)):
        with (target/(action+'.'+suffix)).open('xb') as stream:stream.write(payload)
    print(json.dumps(dict(label=action,accepted=value['accepted'],returncode=code,charged_seconds=charged,
        cumulative_kind_seconds=spent[kind]+charged),sort_keys=True))
    if not value['accepted']:raise SystemExit(1)
