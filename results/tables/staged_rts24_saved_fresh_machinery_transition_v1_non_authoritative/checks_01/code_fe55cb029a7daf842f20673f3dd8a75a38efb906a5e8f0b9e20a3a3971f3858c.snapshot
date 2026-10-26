"""Bounded development actions and reusable direct-child cleanup; no formal owner."""
import time
STARTED=time.perf_counter()
from hashlib import sha256
import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;ROOT=BASE.parents[2]
EXE='D:\\Miniconda3\\envs\\compute\\python.exe'
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
def save(path,value):
    with path.open('xb') as stream:stream.write(raw(value))
def bounded(argv,timeout):
    import ctypes as C
    from ctypes import wintypes as W
    old=ROOT/'results/tables/staged_rts24_saved_fresh_wire_data_v1_non_authoritative/checks_01/run.py'
    expected=read(ROOT/'results/tables/staged_rts24_saved_fresh_import_policy_v2_non_authoritative/checks_01/baseline.json')['preserved'][old.relative_to(ROOT).as_posix()]
    assert pin(old.read_bytes())==expected
    spec=importlib.util.spec_from_file_location('fixed_transition_drain',old);drain=importlib.util.module_from_spec(spec);spec.loader.exec_module(drain)
    drain.STDOUT_CAP=65536;drain.STDERR_CAP=16384
    api=C.WinDLL('kernel32',use_last_error=True);check=api.GetHandleInformation;check.argtypes=[W.HANDLE,C.POINTER(W.DWORD)];check.restype=W.BOOL
    class Counters(C.Structure):
        _fields_=[('cb',W.DWORD),('PageFaultCount',W.DWORD)]+[(n,C.c_size_t) for n in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    mem=C.WinDLL('psapi',use_last_error=True).GetProcessMemoryInfo;mem.argtypes=[W.HANDLE,C.POINTER(Counters),W.DWORD];mem.restype=W.BOOL
    process=None;code=None;stdout=stderr=b'';error=None;state=None;closed=False;peak=None;cleanup=[]
    try:
        if timeout<=0:raise TimeoutError('no target budget')
        process=subprocess.Popen(argv,executable=EXE,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        code,stdout,stderr,error,state=drain.drain(process,timeout)
        counters=Counters();counters.cb=C.sizeof(counters)
        if mem(W.HANDLE(int(process._handle)),C.byref(counters),counters.cb):peak=int(counters.PeakWorkingSetSize)
    except BaseException as caught:error=type(caught).__name__
    finally:
        if process is not None:
            try:
                if process.poll() is None:
                    try:process.kill()
                    except BaseException as caught:cleanup.append('kill:'+type(caught).__name__)
                    try:process.wait(timeout=1.)
                    except BaseException as caught:cleanup.append('wait:'+type(caught).__name__)
            except BaseException as caught:cleanup.append('poll:'+type(caught).__name__)
            finally:
                try:
                    handle=int(process._handle)
                    try:process._handle.Close()
                    finally:
                        flags=W.DWORD();C.set_last_error(0)
                        closed=process._handle.closed and not check(W.HANDLE(handle),C.byref(flags)) and C.get_last_error()==6
                except BaseException as caught:cleanup.append('handle:'+type(caught).__name__)
    return code,stdout,stderr,error,dict(bounded_drain=state,handle_closed=closed,peak_working_set_bytes=peak,cleanup=cleanup)
def storage(extra_files,extra_bytes):
    files=[p for p in BASE.rglob('*') if p.is_file()]
    assert len(files)+extra_files<=48 and sum(p.stat().st_size for p in files)+extra_bytes<=2*1024**2
def snapshot(blob):
    sha=sha256(blob).hexdigest()
    for root in (BASE,ROOT/'results/tables/staged_rts24_saved_fresh_import_policy_cold_v1_non_authoritative',ROOT/'results/tables/staged_rts24_saved_fresh_import_policy_v2_non_authoritative',ROOT/'results/tables/staged_rts24_saved_fresh_import_policy_v1_non_authoritative',ROOT/'results/tables/staged_rts24_saved_fresh_wire_data_v1_non_authoritative',ROOT/'results/tables/staged_rts24_saved_fresh_role_data_v1_non_authoritative'):
        for path in root.glob('checks_*/code_'+sha+'.snapshot'):
            assert path.read_bytes()==blob;return
    with (OUT/('code_'+sha+'.snapshot')).open('xb') as stream:stream.write(blob)
def main(action):
    baseline=read(OUT/'baseline.json');cap=baseline['phase_caps'][action];kind='pytest' if action.startswith('pytest_') else 'static'
    prior={p.relative_to(ROOT).as_posix():read(p) for p in OUT.glob('*.exit.json')}
    revisions=[p for p in (OUT/'revision.json',OUT/'revision_02.json') if p.exists()]
    revision_cost=sum(read(p)['registration_charged_seconds'] for p in revisions)
    spent={k:sum(r['charged_seconds'] for r in prior.values() if r['kind']==k)+(baseline['registration_charged_seconds']+revision_cost if k=='static' else 0) for k in ('static','pytest')}
    assert spent[kind]+cap<=(60 if kind=='static' else 45) and sum(spent.values())+cap<=105
    for suffix in ('stdout.log','stderr.log','exit.json'):assert not (OUT/(action+'.'+suffix)).exists()
    before_source=names(ROOT/n for n in baseline['source_names']);before_helpers=names(OUT.glob('*.py'))
    control_names=('baseline.json','import_policy.json',*(p.name for p in revisions))
    before_controls=names(OUT/n for n in control_names)
    profile=read(OUT/'import_policy.json');external={profile['executable_path']:profile['executable_pin'],**profile['external_sources']}
    assert {n:pin(Path(n).read_bytes()) for n in external}==external and before_controls[(OUT/'import_policy.json').relative_to(ROOT).as_posix()]==baseline['policy_pin']
    collecting=action in ('collection','collection_repair')
    combined=action in ('pytest_main','pytest_repair') and (OUT/'revision.json').exists()
    admission_name='admission_repair.json' if (OUT/'pytest_repair.exit.json').exists() else 'admission.json'
    if combined:
        revision=read(OUT/'revision.json')
        assert read(OUT/'collection.exit.json')['accepted'] is False and names(ROOT/n for n in revision['preserved_pins'])==revision['preserved_pins']
        old=read(OUT/'collection.exit.json');assert revision['previous_helper_pins']==old['helper_pins']==old['after_helper_pins']
        previous_path=ROOT/'results/tables/staged_rts24_saved_fresh_import_policy_cold_v1_non_authoritative/checks_01/regression_admission.json'
        assert revision['preserved_pins'][previous_path.relative_to(ROOT).as_posix()]==pin(previous_path.read_bytes())
        assert revision['predecessor_nodes']==read(previous_path)['groups']['pytest_regression']
        if (OUT/'revision_02.json').exists():
            revision2=read(OUT/'revision_02.json');assert action=='pytest_repair'
            main_row=read(OUT/'pytest_main.exit.json');assert main_row['accepted'] and revision2['main_accepted_but_environment_finding']
            assert names(ROOT/n for n in revision2['preserved_pins'])==revision2['preserved_pins']
            assert revision['current_helper_pins']==main_row['helper_pins']==revision2['previous_helper_pins']
            assert revision2['current_helper_pins']==before_helpers
        else:assert action=='pytest_main' and revision['current_helper_pins']==before_helpers
    assert not collecting or not revisions
    if not collecting and not combined:
        anchor=read(OUT/('pytest_repair.exit.json' if admission_name=='admission_repair.json' else 'pytest_main.exit.json'));plan=read(OUT/admission_name)
        assert anchor['accepted'] and anchor['child_artifact_pins'][(OUT/admission_name).relative_to(ROOT).as_posix()]==pin((OUT/admission_name).read_bytes())
        assert plan['source_pins']==before_source and plan['helper_pins']==before_helpers and plan['controls_pins']==before_controls
    for name in {*before_helpers,'experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py'}:snapshot((ROOT/name).read_bytes())
    storage(10 if action=='cold' else 3,400000)
    args=['--collect-only',action] if collecting else ['--collect-and-run',action] if combined else [admission_name,action] if kind=='pytest' else [action]
    script=OUT/'pytest_harness.py' if collecting or kind=='pytest' else OUT/'cold.py' if action=='cold' else OUT/'oracle.py'
    preparation=time.perf_counter()-STARTED;timeout=cap-2.5-preparation;argv=[EXE,'-B',str(script),*args]
    started=time.perf_counter();code,stdout,stderr,error,state=bounded(argv,timeout);target=time.perf_counter()-started
    expected=['admission_repair.json' if action=='collection_repair' else 'admission.json',action+'.harness.json'] if collecting else [action+'.harness.json','admission_repair.json' if action=='pytest_repair' else 'admission.json'] if combined else [action+'.harness.json'] if kind=='pytest' else [f'cold_{case}.{suffix}' for case in ('normal','caught_effect','blocked_installation') for suffix in ('stdout.log','stderr.log','json')] if action=='cold' else [action+'_report.json']
    paths=[OUT/n for n in expected];missing=[p.relative_to(ROOT).as_posix() for p in paths if not p.exists()];produced=names(p for p in paths if p.exists())
    after_source=names(ROOT/n for n in before_source);after_helpers=names(ROOT/n for n in before_helpers);after_controls=names(ROOT/n for n in before_controls)
    external_after={n:pin(Path(n).read_bytes()) for n in external}
    post_ok=before_source==after_source and before_helpers==after_helpers and before_controls==after_controls and external==external_after and not missing
    charged=time.perf_counter()-STARTED+.5
    successor={k:spent[k]+(charged if k==kind else 0) for k in spent}
    value=dict(authority='DRAFT_NONAUTHORITATIVE',label=action,kind=kind,argv=argv,returncode=code,error=error,
        accepted=code==0 and error is None and post_ok and state['handle_closed'] and not state['cleanup'] and charged<=cap,
        source_pins=before_source,after_source_pins=after_source,source_epoch=sha256(raw(before_source)).hexdigest(),helper_pins=before_helpers,after_helper_pins=after_helpers,
        controls_pins=before_controls,after_controls_pins=after_controls,external_pins=external,after_external_pins=external_after,
        child_artifact_pins=produced,missing_child_artifacts=missing,postcheck_pins_match=post_ok,
        charged_seconds=charged,cap_seconds=cap,tail_reserve_seconds=.5,preparation_seconds=preparation,target_seconds=target,target_timeout_seconds=timeout,
        stdout_pin=pin(stdout),stderr_pin=pin(stderr),process_observation=state,
        raw_streams_embedded=True,stdout_raw_base64=base64.b64encode(stdout).decode('ascii'),stderr_raw_base64=base64.b64encode(stderr).decode('ascii'),
        prior_record_pins={n:pin((ROOT/n).read_bytes()) for n in prior},previous_charged_seconds=spent,successor_charged_seconds=successor,
        predecessor_charged_seconds=baseline['predecessor_charged_seconds'],all_cumulative_charged_seconds={k:baseline['predecessor_charged_seconds'][k]+successor[k] for k in successor},
        actual_F=False,run_authority=False,resource_admission=False,formal_result=False,predecessor_resource_admission=False)
    blob=raw(value);storage(1,len(blob))
    with (OUT/(action+'.exit.json')).open('xb') as stream:stream.write(blob)
    print(json.dumps(dict(label=action,accepted=value['accepted'],charged_seconds=charged,successor_charged_seconds=successor),sort_keys=True))
    if not value['accepted']:raise SystemExit(1)
if __name__=='__main__':
    try:main(sys.argv[1])
    except BaseException as caught:
        label=sys.argv[1];path=OUT/(label+'.exit.json')
        if not path.exists():save(path,dict(authority='DRAFT_NONAUTHORITATIVE',label=label,kind='pytest' if label.startswith('pytest_') else 'static',accepted=False,partial_capture=True,error_type=type(caught).__name__,charged_seconds=time.perf_counter()-STARTED+.5,actual_F=False,run_authority=False,resource_admission=False,formal_result=False))
        raise
