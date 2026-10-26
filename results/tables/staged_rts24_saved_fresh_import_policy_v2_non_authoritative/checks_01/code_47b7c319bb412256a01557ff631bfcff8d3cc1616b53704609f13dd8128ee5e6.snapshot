"""Continue the original cumulative budget; immutable predecessor captures remain bound."""
import time
STARTED=time.perf_counter()
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;ROOT=BASE.parents[2];PACKAGE=BASE/'final_package_01'
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
BASELINE_RAW=(OUT/'baseline.json').read_bytes()
baseline=json.loads(BASELINE_RAW)
OLD_DATA=ROOT/'results/tables/staged_rts24_saved_fresh_wire_data_v1_non_authoritative'
OLD_POLICY=ROOT/'results/tables/staged_rts24_saved_fresh_import_policy_v1_non_authoritative'
old=OLD_DATA/'checks_01/run.py';assert pin(old.read_bytes())==baseline['preserved'][old.relative_to(ROOT).as_posix()]
spec=importlib.util.spec_from_file_location('pinned_bounded_capture',old);capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
def controls():return names(OUT/n for n in ('baseline.json','import_policy.json','runtime_profile_v3_proposal.json','revision_final.json'))
def sources():return names(ROOT/n for n in baseline['sources'])
def helpers():return names(p for d in (OUT,PACKAGE) for p in d.glob('*.py'))
def fixed():
    expected=baseline['preserved']
    assert names(ROOT/n for n in expected)==expected,'historical exact bytes changed'
    actual=sources();assert all(actual[n]==p for n,p in baseline['sources'].items() if n not in (
        'experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py'))
    return pin(raw(expected))
def snapshot(data):
    for d in (OLD_POLICY/'checks_01',OLD_DATA/'checks_02',OLD_DATA/'checks_01',ROOT/'results/tables/staged_rts24_saved_fresh_role_data_v1_non_authoritative/checks_01',OUT):
        p=d/('code_'+sha256(data).hexdigest()+'.snapshot')
        if p.exists():assert p.read_bytes()==data;return
    with p.open('xb') as stream:stream.write(data)
def storage(reserve_files,reserve_bytes):
    files=[p for p in BASE.rglob('*') if p.is_file()]
    assert len(files)+reserve_files<=64 and sum(p.stat().st_size for p in files)+reserve_bytes<=4*1024**2
if __name__=='__main__':
    action=sys.argv[1];revision=read(OUT/'revision_final.json');caps=revision['phase_caps'];assert action in caps
    assert names(ROOT/n for n in revision['original_artifact_pins'])==revision['original_artifact_pins']
    assert sources()==revision['source_pins'] and helpers()==revision['helper_pins']
    cap=caps[action];kind='pytest' if action.startswith('pytest_') else 'static'
    target=OUT if action in ('collection_final','pytest_a','cold_import') else PACKAGE
    script=OUT/'cold_import_revision_02.py' if action=='cold_import' else OUT/'pytest_harness_revision_02.py' if target==OUT else PACKAGE/'oracle_revision_02.py'
    args=['--collect-only',action] if action=='collection_final' else ['admission_final.json',action] if kind=='pytest' else [action]
    records={p.relative_to(ROOT).as_posix():read(p) for d in (OLD_DATA/'checks_01',OLD_DATA/'final_package_01',OLD_DATA/'checks_02',OLD_DATA/'final_package_02',OLD_POLICY/'checks_01',OUT,PACKAGE) for p in d.glob('*.exit.json')}
    spent={k:sum(v['charged_seconds'] for v in records.values() if v['kind']==k) for k in ('static','pytest')}
    assert spent[kind]+cap<=(120 if kind=='static' else 420) and sum(spent.values())+cap<=540
    for suffix in ('stdout.log','stderr.log','exit.json'):assert not (target/(action+'.'+suffix)).exists()
    before_controls=controls();assert before_controls[(OUT/'baseline.json').relative_to(ROOT).as_posix()]==pin(BASELINE_RAW)
    if action!='collection_final':
        anchor=read(OUT/'collection_final.exit.json')['child_artifact_pins']
        assert anchor[(OUT/'revision_final.json').relative_to(ROOT).as_posix()]==pin((OUT/'revision_final.json').read_bytes())
        assert anchor[(OUT/'admission_final.json').relative_to(ROOT).as_posix()]==pin((OUT/'admission_final.json').read_bytes())
        assert read(OUT/'admission_final.json')['controls_pins']==before_controls
    before_source=sources();before_helpers=helpers();before_fixed=fixed()
    for n in {*before_source,*before_helpers}:snapshot((ROOT/n).read_bytes())
    storage(12 if action=='cold_import' else 5 if action=='collection_final' else 5 if action=='saved' else 4,1100000 if action=='cold_import' else 650000 if action=='collection_final' else 370000)
    preparation=time.perf_counter()-STARTED;timeout=cap-3.-preparation
    argv=[sys.executable,'-B',str(script),*args];started=time.perf_counter()
    if timeout<=0:raise RuntimeError('preparation exhausted; no child launched')
    code,stdout,stderr,error,state=capture.spawn_and_drain(argv,timeout)
    target_seconds=time.perf_counter()-started
    produced_names=['admission_final.json','collection_final.harness.json','revision_final.json'] if action=='collection_final' else [action+'.harness.json'] if kind=='pytest' else [f'cold_{case}.{suffix}' for case in baseline['cold_cases'] for suffix in ('stdout.log','stderr.log','json')] if action=='cold_import' else ['checkpoint_freeze.json','saved_report.json'] if action=='saved' else [action+'_report.json']
    produced_paths=[(OUT if target==OUT else PACKAGE)/name for name in produced_names]
    missing=[p.relative_to(ROOT).as_posix() for p in produced_paths if not p.exists()]
    produced=names(p for p in produced_paths if p.exists())
    after_source=sources();after_helpers=helpers();after_fixed=fixed();after_controls=controls()
    post_ok=before_source==after_source and before_helpers==after_helpers and before_fixed==after_fixed and before_controls==after_controls and not missing
    charged=time.perf_counter()-STARTED+.5
    value=dict(authority='DRAFT_NONAUTHORITATIVE',label=action,kind=kind,argv=argv,returncode=code,error=error,
        child_artifact_pins=produced,missing_child_artifacts=missing,accepted=code==0 and error is None and post_ok and charged<=cap,source_pins=before_source,helper_pins=before_helpers,controls_pins=before_controls,after_controls_pins=after_controls,
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
