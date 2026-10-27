"""Finite guard successor: complete native roots and immutable mutation targets."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time

OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2];OLD=ROOT/'results/tables/staged_rts24_saved_fresh_runtime_handoff_v1_non_authoritative'
EXE='D:/Miniconda3/envs/compute/python.exe'
CORE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v7.py'
PARENT=ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v3.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v3.py'
TEST=ROOT/'tests/test_staged_rts24_saved_fresh_runtime_handoff_v3.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_runtime_guard_scope_v1.md'
CAPTURE=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/capture.py'
NAMESPACE=ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_v2.py'
IMPORT=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_v3.py'
CASES=('normal','precommit','postcommit','blocked_installation','handoff_middle','M_only','after_D')
PHASES=('unittest','pre_seal','discovery','profile_admission','import_discovery','import_admission','probes','saved')
OLD_MAP_SHA='bc8b33b0dc2cb66436e4cc467cc65563866b8e636d85b817cb035d8aa55f5580'

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
    assert len(rows)==17 and sum(v['bytes'] for v in rows.values())==771531 and pin(canonical(rows))['sha256']==OLD_MAP_SHA,'frozen WIP tree changed'
    return rows
def predecessor():
    old_map();reg=read(OLD/'repair_registration.json');saved=read(OLD/'wip_snapshot.json')
    assert saved['accepted'] is True and saved['status']=='WIP_PRE_SEAL_OPEN' and saved['cold_children_launched']==0
    for path,expected in {**reg['input_pins'],**saved['input_and_artifact_pins']}.items():assert pin(Path(path).read_bytes())==expected,path
    assert read(OLD/'unittest_repair_report.json')['tests_run']==20 and read(OLD/'unittest.exit.json')['accepted'] is False
    return reg,saved['all_cumulative_charged_seconds']

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
    result[kind]+=extra;return result

def prerequisites(action,reg):
    preceding=list(PHASES[:PHASES.index(action)])
    assert sorted(p.name for p in OUT.glob('*.exit.json'))==sorted(n+'.exit.json' for n in preceding)
    held=pins([OUT/'registration.json'])
    for name in preceding:
        p=OUT/(name+'.exit.json');r=read(p)
        assert r['accepted'] is True and r['label']==name and r['registration_pin']==held[str(OUT/'registration.json')]
        assert r['helper_pins']==reg['helper_pins'] and r['source_epoch']==reg['source_epoch']
        for path,value in r['produced_and_control_pins'].items():assert pin(Path(path).read_bytes())==value,path
        held.update(pins([p]))
    return held

def register():
    started=time.perf_counter();target=OUT/'registration.json';assert not target.exists()
    try:
        previous,old_scope_cost=predecessor();parent=load(PARENT,'namespace_register_parent');assert parent.source()==previous['source_pins']
        helpers=[CORE,PARENT,PROBE,NAMESPACE,IMPORT,TEST,Path(__file__).absolute()];helper_pins=pins(helpers)
        save(OUT/'helper_snapshots.json',{str(p):base64.b64encode(p.read_bytes()).decode('ascii') for p in helpers})
        code=parent.transport()
        with (OUT/'transport.snapshot').open('xb') as f:f.write(code)
        import subprocess
        sample=[EXE,'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(OUT/'probe_blocked_installation.plan.json'),'0'*64]
        units=len(subprocess.list2cmdline(sample).encode('utf-16-le'))//2;assert units<=30000
        cls=next(n for n in ast.parse(TEST.read_bytes()).body if isinstance(n,ast.ClassDef) and n.name=='RuntimeHandoffTests')
        nodes=sorted('runtime_handoff_tests.RuntimeHandoffTests.'+n.name for n in cls.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_'))
        fixed=set(Path(p) for p in previous['input_pins']);fixed.update(helpers+[SCOPE,OUT/'import_policy.json'])
        fixed.update(p for p in OLD.rglob('*') if p.is_file());fixed.update([OUT/'helper_snapshots.json',OUT/'transport.snapshot'])
        inputs=pins(sorted(fixed));cost=time.perf_counter()-started
        assert cost<=3 and usage()['files']+1<=40 and usage()['bytes']<=8*1024**2
        save(target,dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',input_pins=inputs,helper_pins=helper_pins,
            source_epoch=previous['source_epoch'],source_pins=previous['source_pins'],transport_pin=pin(code),command_utf16_units=units,unit_nodes=nodes,
            registration_charged_seconds=cost,old_tree_map_sha256=pin(canonical(old_map()))['sha256'],prior_not_accepted_count=16,
            predecessor_charged_seconds=old_scope_cost,old_scope_charged_seconds=read(OLD/'wip_snapshot.json')['scope_charged_seconds'],caps=dict(static=80,unittest=30,total=110,files=40,bytes=8*1024**2),
            phase_caps=dict(unittest=18,pre_seal=1,discovery=8,profile_admission=3,import_discovery=10,import_admission=3,probes=40,saved=6),
            actual_F=False,run_authority=False,resource_admission=False,formal_result=False,production_seal=False))
        print(canonical(dict(accepted=True,registration_charged_seconds=cost,unit_nodes=len(nodes),transport_pin=pin(code))).decode())
    except BaseException as error:
        save(OUT/'registration_failure.json',dict(accepted=False,kind='static',charged_seconds=time.perf_counter()-started,error=repr(error),actual_F=False,run_authority=False));raise

def unit_child():
    import unittest
    reg=read(OUT/'registration.json');check(reg);module=load(TEST,'runtime_handoff_tests');suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    def nodes(s):return [n for c in s for n in nodes(c)] if isinstance(s,unittest.TestSuite) else [s.id()]
    actual=sorted(nodes(suite));assert actual==reg['unit_nodes']
    save(OUT/'unittest_admission.json',dict(nodes=actual,helper_pins=reg['helper_pins'],before_test_calls=True))
    admission=pin((OUT/'unittest_admission.json').read_bytes());result=unittest.TextTestRunner(verbosity=1).run(suite)
    check(reg);assert admission==pin((OUT/'unittest_admission.json').read_bytes())
    report=dict(accepted=result.wasSuccessful() and result.testsRun==len(actual) and not result.skipped,nodes=actual,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),admission_pin=admission)
    save(OUT/'unittest_report.json',report)
    if not report['accepted']:raise SystemExit(1)
    print(canonical(dict(accepted=True,unit_nodes=len(actual))).decode())

def saved_child():
    reg=read(OUT/'registration.json');check(reg);held=prerequisites('saved',reg);admission=read(OUT/'profile_admission.json')
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
    reg=read(OUT/'registration.json');cap=reg['phase_caps'][action];kind='unittest' if action=='unittest' else 'static'
    accepted=False;error=None;held=None;streams=None;results=[];control=pin((OUT/'registration.json').read_bytes())
    try:
        assert reg['accepted'] is True;check(reg);held=prerequisites(action,reg);budget=spent(cap,kind)
        assert budget[kind]<=reg['caps'][kind] and sum(budget.values())<=110
        parent=load(PARENT,'descriptor_parent');assert pin(parent.transport())==reg['transport_pin']
        if action in ('unittest','saved'):
            capture=load(CAPTURE,'descriptor_capture');label='unit_child' if action=='unittest' else 'saved_child'
            rc,out,err,why,obs=capture.bounded([EXE,'-B','-s',str(Path(__file__).absolute()),label],cap-(time.perf_counter()-started)-0.7)
            streams=dict(returncode=rc,stdout_raw_base64=base64.b64encode(out).decode(),stderr_raw_base64=base64.b64encode(err).decode(),stdout_pin=pin(out),stderr_pin=pin(err),error=why,process_observation=obs)
            drain=obs['bounded_drain'];assert rc==0 and why is None and obs['handle_closed'] and not obs['cleanup']
            assert drain['reader_threads_terminal'] and drain['pipes_closed'] and not drain['reader_errors'] and not drain['cleanup'] and not drain['stdout_truncated'] and not drain['stderr_truncated']
            assert read(OUT/(action+'_report.json'))['accepted'] is True
        elif action=='pre_seal':
            summary=read(OUT/'pre_seal_findings.json')
            assert summary['authority']=='DRAFT_NONAUTHORITATIVE' and summary['official_review'] is False and summary['must_fix_open']==[]
            assert summary['helper_pins']==reg['helper_pins'] and summary['unittest_report_pin']==pin((OUT/'unittest_report.json').read_bytes())
            assert summary['three_findings_closed_by_named_tests'] and summary['cold_diagnostic_only'] and summary['run_authority'] is False
            save(OUT/'pre_seal_admission.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',scope='bounded_development_diagnostics_only',
                helper_pins=reg['helper_pins'],findings_pin=pin((OUT/'pre_seal_findings.json').read_bytes()),registration_pin=control,
                official_review=False,production_seal=False,actual_F=False,run_authority=False,resource_admission=False,formal_result=False))
        elif action in ('discovery','import_discovery'):
            result=parent.one_case(action,cap-(time.perf_counter()-started));results.append(result);assert result['accepted']
        elif action=='profile_admission':
            discovery=read(OUT/'probe_discovery.receipt.json');assert discovery['accepted'] is True
            profile=read(OUT/'startup_profile.json');assert profile['bootstrap_pin']==reg['transport_pin']
            for p,value in profile['disk_file_observations'].items():assert pin(Path(p).read_bytes())==value
            save(OUT/'profile_admission.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',profile_pin=pin((OUT/'startup_profile.json').read_bytes()),
                transport_pin=reg['transport_pin'],helper_pins=reg['helper_pins'],environment_pin=pin(canonical(parent.environment())),
                discovery_receipt_pin=pin((OUT/'probe_discovery.receipt.json').read_bytes()),registration_pin=control,
                actual_F=False,run_authority=False,resource_admission=False,formal_result=False))
        elif action=='import_admission':
            discovery=read(OUT/'probe_import_discovery.receipt.json');assert discovery['accepted'] is True
            profile=read(OUT/'import_profile.json')
            assert profile==discovery['result']['child_record']['import_profile']
            assert profile['machinery_observed']==profile['machinery_authenticated']==2 and profile['optional_attempts']==1
            save(OUT/'import_admission.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',profile_pin=pin((OUT/'import_profile.json').read_bytes()),
                transport_pin=reg['transport_pin'],helper_pins=reg['helper_pins'],discovery_receipt_pin=pin((OUT/'probe_import_discovery.receipt.json').read_bytes()),
                registration_pin=control,actual_F=False,run_authority=False,resource_admission=False,formal_result=False))
        elif action=='probes':
            assert not (OUT/'probe_cases.receipts.jsonl').exists();admission_pin=pin((OUT/'profile_admission.json').read_bytes())
            for case in CASES:
                requested=8 if case=='normal' else 5
                assert cap-(time.perf_counter()-started)-.5>=requested,'no full case budget; do not launch'
                result=parent.one_case(case,requested);results.append(result);assert result['accepted'],case
                assert (OUT/'probe_cases.receipts.jsonl').read_bytes()==b''.join(canonical(row)+b'\n' for row in results)
                check(reg);assert admission_pin==pin((OUT/'profile_admission.json').read_bytes())
        else:raise ValueError('fixed descriptor repair action')
        check(reg);assert control==pin((OUT/'registration.json').read_bytes()) and held==prerequisites(action,reg)
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
