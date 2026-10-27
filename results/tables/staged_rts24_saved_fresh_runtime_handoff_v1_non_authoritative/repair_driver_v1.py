"""Explicit one-time unit timeout repair; frozen original helpers and charges."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time

OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2];OLD=ROOT/'results/tables/staged_rts24_saved_fresh_entry_namespace_startup_repair_v1_non_authoritative'
EXE='D:/Miniconda3/envs/compute/python.exe'
CORE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v6.py'
PARENT=ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v2.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v2.py'
TEST=ROOT/'tests/test_staged_rts24_saved_fresh_runtime_handoff_v2.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_runtime_handoff_scope_v1.md'
CAPTURE=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/capture.py'
NAMESPACE=ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_v2.py'
IMPORT=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_v2.py'
CASES=('normal','precommit','postcommit','blocked_installation','handoff_middle','M_only','after_D')
PHASES=('unittest_repair','discovery','profile_admission','import_discovery','import_admission','probes','saved')
OLD_MAP_SHA='0fa866ffc408114be70fb623cf498e2d54e49f6cfd7ab1b70bea7bd25098b24a'

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(p):return json.loads(p.read_bytes())
def save(p,v):
    with p.open('xb') as f:f.write(canonical(v))
def pins(paths):return {str(p):pin(p.read_bytes()) for p in paths}
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def old_map():
    rows={str(p.relative_to(OLD)):pin(p.read_bytes()) for p in sorted(OLD.rglob('*')) if p.is_file()}
    assert len(rows)==23 and sum(p['bytes'] for p in rows.values())==516840,'predecessor retention changed'
    return rows
def predecessor():
    old_map();reg=read(OLD/'registration.json');saved=read(OLD/'saved.exit.json')
    assert saved['accepted'] is True and read(OLD/'saved_report.json')['accepted'] is True
    for path,expected in {**reg['input_pins'],**saved['produced_and_control_pins']}.items():assert pin(Path(path).read_bytes())==expected,path
    assert read(OLD/'unittest_report.json')['tests_run']==26
    return reg,dict(static=168.81606540001235,pytest=366.48897970000326,unittest=10.109085399999458)

def check(reg):
    predecessor()
    for path,expected in reg['input_pins'].items():assert pin(Path(path).read_bytes())==expected,path
def usage():
    files=[p for p in OUT.rglob('*') if p.is_file()];return dict(files=len(files),bytes=sum(p.stat().st_size for p in files))
def spent(extra=0,kind='static'):
    result=dict(static=0.0,unittest=0.0)
    for p in OUT.glob('*.exit.json'):
        r=read(p);result[r['kind']]+=r['charged_seconds']
    if (OUT/'registration.json').exists():result['static']+=read(OUT/'registration.json')['registration_charged_seconds']
    if (OUT/'repair_registration.json').exists():result['static']+=read(OUT/'repair_registration.json')['registration_charged_seconds']
    result[kind]+=extra;return result

def prerequisites(action,reg):
    preceding=list(PHASES[:PHASES.index(action)])
    assert sorted(p.name for p in OUT.glob('*.exit.json') if p.name!='unittest.exit.json')==sorted(n+'.exit.json' for n in preceding)
    held=pins([OUT/'repair_registration.json'])
    for name in preceding:
        p=OUT/(name+'.exit.json');r=read(p)
        assert r['accepted'] is True and r['label']==name and r['registration_pin']==held[str(OUT/'repair_registration.json')]
        assert r['helper_pins']==reg['helper_pins'] and r['source_epoch']==reg['source_epoch']
        for path,value in r['produced_and_control_pins'].items():assert pin(Path(path).read_bytes())==value,path
        held.update(pins([p]))
    return held

def register():
    started=time.perf_counter();target=OUT/'repair_registration.json';assert not target.exists()
    base=read(OUT/'registration.json');check(base);failed=read(OUT/'unittest.exit.json')
    assert failed['accepted'] is False and failed['streams']['error']=='timeout'
    assert failed['streams']['process_observation']['handle_closed'] and not failed['streams']['process_observation']['cleanup']
    assert base['unit_nodes'] and not (OUT/'unittest_report.json').exists()
    fixed={Path(p) for p in base['input_pins']};fixed.update(p for p in OUT.iterdir() if p.is_file())
    scope=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_runtime_handoff_unit_repair_v1.md';fixed.add(scope)
    helpers=[CORE,PARENT,PROBE,IMPORT,TEST,Path(__file__).absolute()]
    helper_pins={**base['helper_pins'],**pins(helpers)}
    fixed.update(helpers)
    parent=load(PARENT,'runtime_repair_register_parent');code=parent.transport()
    import subprocess
    sample=[EXE,'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(OUT/'probe_blocked_installation.plan.json'),'0'*64]
    assert len(subprocess.list2cmdline(sample).encode('utf-16-le'))//2<=30000
    with (OUT/'transport_repair.snapshot').open('xb') as f:f.write(code)
    fixed.add(OUT/'transport_repair.snapshot')
    cls=next(n for n in ast.parse(TEST.read_bytes()).body if type(n) is ast.ClassDef and n.name=='RuntimeHandoffTests')
    nodes=sorted('runtime_handoff_tests.RuntimeHandoffTests.'+n.name for n in cls.body if type(n) is ast.FunctionDef and n.name.startswith('test_'))
    save(OUT/'repair_helper_snapshots.json',{str(p):base64.b64encode(p.read_bytes()).decode() for p in helpers})
    fixed.add(OUT/'repair_helper_snapshots.json');inputs=pins(sorted(fixed));cost=time.perf_counter()-started
    assert base['registration_charged_seconds']+cost<=3
    reg={**base,'transport_pin':pin(code),'unit_nodes':nodes,'input_pins':inputs,'helper_pins':helper_pins,'registration_charged_seconds':cost,
        'base_registration_pin':pin((OUT/'registration.json').read_bytes()),'prior_not_accepted_count':16,
        'repair_scope_pin':pin(scope.read_bytes()),'phase_caps':dict(unittest_repair=15,discovery=6,profile_admission=3,import_discovery=8,import_admission=3,probes=35,saved=8)}
    save(target,reg);print(canonical(dict(accepted=True,registration_charged_seconds=cost,unit_nodes=len(reg['unit_nodes']))).decode())

def unit_child():
    import unittest
    reg=read(OUT/'repair_registration.json');check(reg);module=load(TEST,'runtime_handoff_tests');suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    def nodes(s):return [n for c in s for n in nodes(c)] if isinstance(s,unittest.TestSuite) else [s.id()]
    actual=sorted(nodes(suite));assert actual==reg['unit_nodes']
    save(OUT/'unittest_repair_admission.json',dict(nodes=actual,helper_pins=reg['helper_pins'],before_test_calls=True))
    admission=pin((OUT/'unittest_repair_admission.json').read_bytes());result=unittest.TextTestRunner(verbosity=1).run(suite)
    check(reg);assert admission==pin((OUT/'unittest_repair_admission.json').read_bytes())
    report=dict(accepted=result.wasSuccessful() and result.testsRun==len(actual) and not result.skipped,nodes=actual,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),admission_pin=admission)
    save(OUT/'unittest_repair_report.json',report)
    if not report['accepted']:raise SystemExit(1)
    print(canonical(dict(accepted=True,unit_nodes=len(actual))).decode())

def saved_child():
    reg=read(OUT/'repair_registration.json');check(reg);held=prerequisites('saved',reg);admission=read(OUT/'profile_admission.json')
    assert admission['profile_pin']==pin((OUT/'startup_profile.json').read_bytes()) and admission['transport_pin']==reg['transport_pin']
    journal=(OUT/'probe_cases.receipts.jsonl').read_bytes();rows=[json.loads(line) for line in journal.splitlines()]
    assert b''.join(canonical(row)+b'\n' for row in rows)==journal and [r['case'] for r in rows]==list(CASES)
    for r in [read(OUT/'probe_discovery.receipt.json'),read(OUT/'probe_import_discovery.receipt.json'),*rows]:
        assert r['accepted'] is True and r['transport_pin']==reg['transport_pin']
        assert r['parent_process_handle_closed'] and r['stdin_closed'] and r['writer_thread_terminal'] and not r['cleanup']
        assert pin(base64.b64decode(r['stdout_raw_base64'],validate=True))==r['stdout_pin'] and pin(base64.b64decode(r['stderr_raw_base64'],validate=True))==r['stderr_pin']
        assert pin((OUT/('probe_'+r['case']+'.plan.json')).read_bytes())==r['plan_pin']
        for flag in ('actual_F','formal_result','run_authority','resource_admission','production_seal'):assert r[flag] is False
    save(OUT/'saved_report.json',dict(accepted=True,probe_journal_pin=pin(journal),profile_admission_pin=pin((OUT/'profile_admission.json').read_bytes()),predecessor_pins=held,
        no_bootstrap_or_scientific_rerun=True,prior_not_accepted_count=16,actual_F=False,formal_result=False,resource_admission=False,run_authority=False))
    check(reg);assert held==prerequisites('saved',reg);print(canonical(dict(accepted=True,saved_receipts=len(rows)+1)).decode())

def run(action):
    started=time.perf_counter();target=OUT/(action+'.exit.json');assert not target.exists()
    reg=read(OUT/'repair_registration.json');cap=reg['phase_caps'][action];kind='unittest' if action=='unittest_repair' else 'static'
    accepted=False;error=None;held=None;streams=None;results=[];control=pin((OUT/'repair_registration.json').read_bytes())
    try:
        assert reg['accepted'] is True;check(reg);held=prerequisites(action,reg);budget=spent(cap,kind)
        assert budget[kind]<=reg['caps'][kind] and sum(budget.values())<=110
        parent=load(PARENT,'descriptor_parent');assert pin(parent.transport())==reg['transport_pin']
        if action in ('unittest_repair','saved'):
            capture=load(CAPTURE,'descriptor_capture');label='unit_child' if action=='unittest_repair' else 'saved_child'
            rc,out,err,why,obs=capture.bounded([EXE,'-B','-s',str(Path(__file__).absolute()),label],cap-(time.perf_counter()-started)-0.7)
            streams=dict(returncode=rc,stdout_raw_base64=base64.b64encode(out).decode(),stderr_raw_base64=base64.b64encode(err).decode(),stdout_pin=pin(out),stderr_pin=pin(err),error=why,process_observation=obs)
            drain=obs['bounded_drain'];assert rc==0 and why is None and obs['handle_closed'] and not obs['cleanup']
            assert drain['reader_threads_terminal'] and drain['pipes_closed'] and not drain['reader_errors'] and not drain['cleanup'] and not drain['stdout_truncated'] and not drain['stderr_truncated']
            assert read(OUT/(action+'_report.json'))['accepted'] is True
        elif action in ('discovery','import_discovery'):
            result=parent.one_case(action,cap-(time.perf_counter()-started));results.append(result);assert result['accepted']
        elif action=='profile_admission':
            discovery=read(OUT/'probe_discovery.receipt.json');assert discovery['accepted'] is True
            profile=read(OUT/'startup_profile.json');assert profile['bootstrap_pin']==reg['transport_pin']
            for p,value in profile['disk_file_observations'].items():assert pin(Path(p).read_bytes())==value
            save(OUT/'profile_admission.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',profile_pin=pin((OUT/'startup_profile.json').read_bytes()),
                transport_pin=reg['transport_pin'],helper_pins=reg['helper_pins'],environment_pin=pin(canonical(parent.environment())),
                discovery_receipt_pin=pin((OUT/'probe_discovery.receipt.json').read_bytes()),registration_pin=reg['base_registration_pin'],repair_registration_pin=control,
                actual_F=False,run_authority=False,resource_admission=False,formal_result=False))
        elif action=='import_admission':
            discovery=read(OUT/'probe_import_discovery.receipt.json');assert discovery['accepted'] is True
            profile=read(OUT/'import_profile.json')
            assert profile==discovery['result']['child_record']['import_profile']
            assert profile['machinery_observed']==profile['machinery_authenticated']==2 and profile['optional_attempts']==1
            save(OUT/'import_admission.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',profile_pin=pin((OUT/'import_profile.json').read_bytes()),
                transport_pin=reg['transport_pin'],helper_pins=reg['helper_pins'],discovery_receipt_pin=pin((OUT/'probe_import_discovery.receipt.json').read_bytes()),
                registration_pin=reg['base_registration_pin'],repair_registration_pin=control,actual_F=False,run_authority=False,resource_admission=False,formal_result=False))
        elif action=='probes':
            assert not (OUT/'probe_cases.receipts.jsonl').exists();admission_pin=pin((OUT/'profile_admission.json').read_bytes())
            for case in CASES:
                requested=6 if case=='normal' else 4.5
                assert cap-(time.perf_counter()-started)-.5>=requested,'no full case budget; do not launch'
                result=parent.one_case(case,requested);results.append(result);assert result['accepted'],case
                assert (OUT/'probe_cases.receipts.jsonl').read_bytes()==b''.join(canonical(row)+b'\n' for row in results)
                check(reg);assert admission_pin==pin((OUT/'profile_admission.json').read_bytes())
        else:raise ValueError('fixed descriptor repair action')
        check(reg);assert control==pin((OUT/'repair_registration.json').read_bytes()) and held==prerequisites(action,reg)
        if action=='probes':assert (OUT/'probe_cases.receipts.jsonl').read_bytes()==b''.join(canonical(row)+b'\n' for row in results)
        accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)[:160]
    charge=time.perf_counter()-started;cost=spent(charge,kind);previous=reg['predecessor_charged_seconds']
    accepted=accepted and charge<=cap and cost[kind]<=reg['caps'][kind] and sum(cost.values())<=110
    artifacts=pins(p for p in OUT.iterdir() if p.is_file() and p.name!='driver.py')
    record=dict(accepted=accepted,label=action,kind=kind,charged_seconds=charge,cap_seconds=cap,charged_seconds_by_kind=cost,
        all_cumulative_charged_seconds=dict(static=previous['static']+cost['static'],pytest=previous['pytest'],unittest=previous['unittest']+cost['unittest']),
        registration_pin=control,source_epoch=reg['source_epoch'],helper_pins=reg['helper_pins'],predecessor_pins=held,produced_and_control_pins=artifacts,
        error=error,streams=streams,case_accepted=[dict(case=r['case'],accepted=r['accepted']) for r in results],
        actual_F=False,run_authority=False,resource_admission=False,formal_result=False,production_seal=False,
        charge_scope='parent preparation through postchecks; editor/review/Git and final exit serialization excluded',storage_before_exit=usage())
    fits=usage()['files']+1<=40 and usage()['bytes']+len(canonical(record))+128<=8*1024**2
    record['storage_cap_satisfied']=fits;record['accepted']=accepted=accepted and fits;save(target,record)
    print(canonical(dict(accepted=accepted,label=action,charged_seconds=charge,error=error)).decode())
    if not accepted:raise SystemExit(1)

if __name__=='__main__':
    if sys.argv[1:]==['register']:register()
    elif sys.argv[1:]==['unit_child']:unit_child()
    elif sys.argv[1:]==['saved_child']:saved_child()
    elif len(sys.argv)==2 and sys.argv[1] in PHASES:run(sys.argv[1])
    else:raise SystemExit('fixed startup repair checks only')
