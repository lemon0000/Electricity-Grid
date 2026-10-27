"""Finite development checks for the conditional pre-ENTRY primitive."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).absolute().parents[3];OUT=Path(__file__).absolute().parent
EXE='D:/Miniconda3/envs/compute/python.exe'
CORE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v1.py'
PARENT=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_parent_v1.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_pre_entry_probe_v1.py'
TEST=ROOT/'tests/test_staged_rts24_saved_fresh_pre_entry_lease_v1.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_pre_entry_lease_scope_v1.md'
PREVIOUS=ROOT/'results/tables/staged_rts24_saved_fresh_root_catalog_v1_non_authoritative'
CAPTURE=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/capture.py'
CASES=('normal','manifest_flip','flags','environment','partial_handle','binding','early_source','transfer','timeout')


def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(p):return json.loads(p.read_bytes())
def save(p,v):
    with p.open('xb') as stream:stream.write(canonical(v))
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def pins(paths):return {str(p):pin(p.read_bytes()) for p in paths}
def usage():
    files=[p for p in OUT.rglob('*') if p.is_file()];return dict(files=len(files),bytes=sum(p.stat().st_size for p in files))
def check(reg):
    for path,expected in reg['input_pins'].items():assert pin(Path(path).read_bytes())==expected,path


def register():
    started=time.perf_counter();target=OUT/'registration.json';assert not target.exists()
    try:
        parent=load(PARENT,'fixed_pre_entry_parent'); sources=parent.source()
        helpers=[CORE,PARENT,PROBE,TEST,Path(__file__).absolute()]
        previous=[p for p in PREVIOUS.rglob('*') if p.is_file()];assert len(previous)==22
        paths=set(previous+[ROOT/n for n in sources]+helpers+[SCOPE,Path(EXE),CAPTURE,parent.DRAIN,
            ROOT/'results/tables/staged_rts24_saved_fresh_wire_contract_v1_non_authoritative/checks_01/baseline.json',parent.SOURCE_CONTROL])
        paths.update(parent.RUNTIME/n for n in ('python312.dll','DLLs/_ctypes.pyd','Lib/ctypes/__init__.py','Lib/ctypes/wintypes.py','Lib/subprocess.py','Lib/encodings/__init__.py'))
        inputs=pins(sorted(paths));helper_pins=pins(helpers)
        for p in helpers:
            raw=p.read_bytes()
            with (OUT/('code_'+pin(raw)['sha256']+'.snapshot')).open('xb') as f:f.write(raw)
        code=parent.transport();assert len(code)<=29000
        with (OUT/'transport.snapshot').open('xb') as f:f.write(code)
        inputs.update(pins([OUT/'transport.snapshot',*[OUT/('code_'+v['sha256']+'.snapshot') for v in helper_pins.values()]]))
        sample=[EXE,'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(OUT/'probe_partial_handle.plan.json'),'0'*64]
        import subprocess
        command_units=len(subprocess.list2cmdline(sample).encode('utf-16-le'))//2;assert command_units<=30000
        cls=next(n for n in ast.parse(TEST.read_bytes()).body if isinstance(n,ast.ClassDef) and n.name=='PreEntryLeaseTests')
        nodes=sorted('pre_entry_tests.PreEntryLeaseTests.'+n.name for n in cls.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_'))
        previous_cost=read(PREVIOUS/'saved.exit.json')['all_cumulative_charged_seconds']
        charge=time.perf_counter()-started
        reg=dict(authority='DRAFT_NONAUTHORITATIVE',accepted=charge<=3,input_pins=inputs,helper_pins=helper_pins,
            source_epoch=parent.SOURCE_SHA,source_pins=sources,transport_pin=pin(code),commandline_sample_utf16_units=command_units,
            unit_nodes=nodes,cases=list(CASES),registration_charged_seconds=charge,predecessor_charged_seconds=previous_cost,
            caps=dict(static=50,unittest=30,total=80,files=64,bytes=8*1024**2),
            phase_caps=dict(unittest=8,unittest_repair=12,discovery=5,profile_admission=2,probes=30,saved=8),
            actual_F=False,run_authority=False,resource_admission=False,formal_result=False,production_seal=False)
        save(target,reg);print(canonical(dict(registered=reg['accepted'],charged_seconds=charge,unit_nodes=len(nodes),transport_bytes=len(code))).decode())
        if not reg['accepted']:raise SystemExit(1)
    except BaseException as error:
        if not target.exists():save(OUT/'registration_failure.json',dict(accepted=False,kind='static',charged_seconds=time.perf_counter()-started,
            error=type(error).__name__,usage=usage(),process_observation=None,actual_F=False,run_authority=False,formal_result=False,resource_admission=False))
        raise


def prerequisites(action,reg):
    names=['unittest','discovery','profile_admission','probes','saved'];expected=names[:names.index(action)]
    assert sorted(p.stem.removesuffix('.exit') for p in OUT.glob('*.exit.json'))==sorted(expected)
    held={}
    for name in expected:
        path=OUT/(name+'.exit.json');record=read(path)
        assert record['accepted'] is True and record['label']==name and record['registration_pin']==pin((OUT/'registration.json').read_bytes())
        assert record['kind']==('unittest' if name=='unittest' else 'static')
        assert record['helper_pins']==reg['helper_pins'] and record['source_epoch']==reg['source_epoch']
        for artifact,expected_pin in record['produced_and_control_pins'].items():
            assert pin(Path(artifact).read_bytes())==expected_pin,artifact
        held.update(pins([path]))
    return held


def unit_child():
    import unittest
    reg=read(OUT/'registration.json');check(reg);module=load(TEST,'pre_entry_tests')
    suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    def nodes(s):return [n for c in s for n in nodes(c)] if isinstance(s,unittest.TestSuite) else [s.id()]
    actual=sorted(nodes(suite));assert actual==reg['unit_nodes']
    save(OUT/'unittest_admission.json',dict(nodes=actual,helper_pins=reg['helper_pins'],before_test_calls=True))
    admission=pin((OUT/'unittest_admission.json').read_bytes());result=unittest.TextTestRunner(verbosity=1).run(suite)
    check(reg);assert admission==pin((OUT/'unittest_admission.json').read_bytes())
    report=dict(accepted=result.wasSuccessful() and result.testsRun==len(actual) and not result.skipped,nodes=actual,
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),admission_pin=admission)
    save(OUT/'unittest_report.json',report)
    if not report['accepted']:raise SystemExit(1)
    print(canonical(dict(accepted=True,unit_nodes=len(actual))).decode())


def saved_child():
    reg=read(OUT/'registration.json');check(reg);held=prerequisites('saved',reg)
    admission=read(OUT/'profile_admission.json');assert admission['profile_pin']==pin((OUT/'startup_profile.json').read_bytes())
    assert admission['transport_pin']==reg['transport_pin']
    rows={}
    for case in ['discovery',*CASES]:
        p=OUT/('probe_'+case+'.receipt.json');r=read(p);assert r['accepted'] is True and r['case']==case
        assert r['parent_process_handle_closed'] and r['stdin_closed'] and r['writer_thread_terminal'] and not r['cleanup']
        assert r['transport_pin']==reg['transport_pin'];rows[p.name]=pin(p.read_bytes())
    for name in ('actual_F','formal_result','run_authority','resource_admission','production_seal'):assert all(read(OUT/('probe_'+c+'.receipt.json'))[name] is False for c in ['discovery',*CASES])
    save(OUT/'saved_report.json',dict(accepted=True,receipt_pins=rows,profile_admission_pin=pin((OUT/'profile_admission.json').read_bytes()),predecessor_pins=held,
        no_bootstrap_or_scientific_rerun=True,actual_F=False,formal_result=False,resource_admission=False,run_authority=False))
    check(reg);assert held==prerequisites('saved',reg)
    print(canonical(dict(accepted=True,saved_receipts=len(rows))).decode())


def run(action):
    started=time.perf_counter();target=OUT/(action+'.exit.json');assert not target.exists()
    reg=read(OUT/'registration.json');cap=reg['phase_caps'][action];kind='unittest' if action.startswith('unittest') else 'static'
    accepted=False;error=None;held=None;streams=None;results=[];control=pin((OUT/'registration.json').read_bytes())
    try:
        assert reg['accepted'] is True;check(reg);held=prerequisites(action,reg)
        prior=[read(p) for p in OUT.glob('*.exit.json')]
        spent={k:sum(v['charged_seconds'] for v in prior if v['kind']==k) for k in ('static','unittest')};spent['static']+=reg['registration_charged_seconds']
        assert spent[kind]+cap<=reg['caps'][kind] and sum(spent.values())+cap<=80
        parent=load(PARENT,'active_pre_entry_parent');assert pin(parent.transport())==reg['transport_pin']
        if action in ('unittest','saved'):
            capture=load(CAPTURE,'pre_entry_outer_capture')
            label='unit_child' if action=='unittest' else 'saved_child'
            rc,out,err,why,obs=capture.bounded([EXE,'-B','-s',str(Path(__file__).absolute()),label],cap-(time.perf_counter()-started)-0.7)
            streams=dict(returncode=rc,stdout_raw_base64=base64.b64encode(out).decode(),stderr_raw_base64=base64.b64encode(err).decode(),stdout_pin=pin(out),stderr_pin=pin(err),error=why,process_observation=obs)
            drain=obs['bounded_drain'];assert rc==0 and why is None and obs['handle_closed'] and not obs['cleanup']
            assert drain['reader_threads_terminal'] and drain['pipes_closed'] and not drain['reader_errors'] and not drain['cleanup'] and not drain['stdout_truncated'] and not drain['stderr_truncated']
            assert read(OUT/(action+'_report.json'))['accepted'] is True
        elif action=='discovery':
            result=parent.one_case('discovery',cap-(time.perf_counter()-started));results.append(result);assert result['accepted']
        elif action=='profile_admission':
            discovery=read(OUT/'probe_discovery.receipt.json');assert discovery['accepted'] is True
            profile=read(OUT/'startup_profile.json');assert profile['bootstrap_pin']==reg['transport_pin']
            for p,value in profile['disk_file_observations'].items():assert pin(Path(p).read_bytes())==value
            save(OUT/'profile_admission.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',profile_pin=pin((OUT/'startup_profile.json').read_bytes()),
                transport_pin=reg['transport_pin'],helper_pins=reg['helper_pins'],environment_pin=pin(canonical(parent.environment())),
                discovery_receipt_pin=pin((OUT/'probe_discovery.receipt.json').read_bytes()),registration_pin=control,
                actual_F=False,run_authority=False,resource_admission=False,formal_result=False))
        elif action=='probes':
            admission_pin=pin((OUT/'profile_admission.json').read_bytes())
            for case in CASES:
                remaining=cap-(time.perf_counter()-started)-0.7;requested=1.5 if case=='timeout' else 3
                assert remaining>=requested,'no full case budget; do not launch'
                result=parent.one_case(case,requested);results.append(result);assert result['accepted'],case
                check(reg);assert admission_pin==pin((OUT/'profile_admission.json').read_bytes())
        else:raise ValueError('fixed development action required')
        check(reg);assert control==pin((OUT/'registration.json').read_bytes()) and held==prerequisites(action,reg)
        accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)[:160]
    charge=time.perf_counter()-started;prior=[read(p) for p in OUT.glob('*.exit.json')]
    spent={k:sum(v['charged_seconds'] for v in prior if v['kind']==k) for k in ('static','unittest')};spent['static']+=reg['registration_charged_seconds'];spent[kind]+=charge
    previous=reg['predecessor_charged_seconds'];accepted=accepted and charge<=cap and spent[kind]<=reg['caps'][kind] and sum(spent.values())<=80
    artifacts=pins(p for p in OUT.iterdir() if p.is_file() and p.name not in ('driver.py',) and not p.name.startswith('code_'))
    record=dict(accepted=accepted,label=action,kind=kind,charged_seconds=charge,cap_seconds=cap,charged_seconds_by_kind=spent,
        all_cumulative_charged_seconds=dict(static=previous['static']+spent['static'],pytest=previous['pytest'],unittest=previous['unittest']+spent['unittest']),
        registration_pin=control,source_epoch=reg['source_epoch'],helper_pins=reg['helper_pins'],predecessor_pins=held,produced_and_control_pins=artifacts,
        error=error,streams=streams,case_receipt_pins={v['case']:pin((OUT/('probe_'+v['case']+'.receipt.json')).read_bytes()) for v in results},
        actual_F=False,run_authority=False,resource_admission=False,formal_result=False,production_seal=False,
        charge_scope='parent preparation through postchecks; editor/review/Git and final exit serialization excluded',storage_before_exit=usage(),storage_cap_satisfied=True)
    projected=len(canonical(record))+2;fits=usage()['files']+1<=64 and usage()['bytes']+projected<=8*1024**2
    record['storage_cap_satisfied']=fits;record['accepted']=accepted=accepted and fits
    save(target,record);print(canonical(dict(accepted=accepted,label=action,charged_seconds=charge)).decode())
    if not accepted:raise SystemExit(1)


if __name__=='__main__':
    if sys.argv[1:]==['register']:register()
    elif sys.argv[1:]==['unit_child']:unit_child()
    elif sys.argv[1:]==['saved_child']:saved_child()
    elif len(sys.argv)==2 and sys.argv[1] in ('unittest','discovery','profile_admission','probes','saved'):run(sys.argv[1])
    else:raise SystemExit('fixed pre-entry development checks only')
