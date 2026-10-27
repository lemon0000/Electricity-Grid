"""Create-only repair lineage; the executed original driver remains immutable."""
import ast
import base64
import difflib
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).absolute().parents[3]; OUT=Path(__file__).absolute().parent
EXE='D:/Miniconda3/envs/compute/python.exe'
CORE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v1.py'
PARENT=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_parent_v1.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_pre_entry_probe_v1.py'
TEST=ROOT/'tests/test_staged_rts24_saved_fresh_pre_entry_lease_v1.py'
REPAIR_SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_pre_entry_cookie_repair_v1.md'
CAPTURE=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/capture.py'
CASES=('normal','manifest_flip','flags','environment','partial_handle','binding','early_source','transfer','timeout')
PHASES=('unittest_repair','discovery_repair','profile_admission','probes','saved')
REG_SHA='41ceeec26cd4664b377ad6556acf41804330916f8361262af69cd322dc6a1aff'
DELTA_SHA='ca025e3e82421212d91ea24950ec0408f2bee7c9e19d9a83f1ae5adffae41cb3'

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(p):return json.loads(p.read_bytes())
def save(p,v):
    with p.open('xb') as f:f.write(canonical(v))
def pins(paths):return {str(p):pin(p.read_bytes()) for p in paths}
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def usage():
    files=[p for p in OUT.rglob('*') if p.is_file()];return dict(files=len(files),bytes=sum(p.stat().st_size for p in files))
def original():
    assert pin((OUT/'registration.json').read_bytes())['sha256']==REG_SHA
    assert pin((OUT/'unittest.exit.json').read_bytes())==dict(bytes=3850,sha256='72eed60643b8f72ea042ae24b569a5dbd16fd45814bc9358a207b3968af3cb13')
    assert pin((OUT/'discovery.exit.json').read_bytes())==dict(bytes=4023,sha256='9815613c2ff1e3c3a4ec2d0bcda6d82757b11403aca5be72fb0ff64ca49a459d')
    reg=read(OUT/'registration.json'); unit=read(OUT/'unittest.exit.json'); failed=read(OUT/'discovery.exit.json')
    assert reg['accepted'] is unit['accepted'] is True and failed['accepted'] is False
    assert unit['label']=='unittest' and failed['label']=='discovery' and failed['error']=='AssertionError:'
    for record in (unit,failed):
        assert record['registration_pin']==pin((OUT/'registration.json').read_bytes())
        assert record['helper_pins']==reg['helper_pins'] and record['source_epoch']==reg['source_epoch']
        for path,expected in record['produced_and_control_pins'].items():assert pin(Path(path).read_bytes())==expected,path
    receipt=read(OUT/'probe_discovery.receipt.json');drain=receipt['bounded_drain']
    assert receipt['accepted'] is False and receipt['child_exit']==1 and receipt['primary']=='AssertionError:' and receipt['cleanup']==[]
    assert receipt['parent_process_handle_closed'] and receipt['writer_thread_terminal'] and receipt['stdin_closed']
    assert drain['pipes_closed'] and drain['reader_threads_terminal'] and not drain['killed'] and not drain['cleanup'] and not drain['reader_errors']
    out=base64.b64decode(receipt['stdout_raw_base64'],validate=True);err=base64.b64decode(receipt['stderr_raw_base64'],validate=True)
    assert pin(out)==receipt['stdout_pin'] and pin(err)==receipt['stderr_pin']
    image=json.loads(out)
    assert image['status']=='discovery_only' and image['dll_directory_close_returned'] is True and image['self_handles_closed'] is None
    assert image['primary'] is None and image['secondary']==[] and image['local_pre_entry_continuity_was_held_and_consumed'] is False
    assert b'SystemExit: 0' in err and b'TypeError: Provided cookie was not returned from os.add_dll_directory' in err
    return reg
def check(rev):
    original()
    for path,expected in rev['input_pins'].items():assert pin(Path(path).read_bytes())==expected,path
def spent(reg,extra=0,kind='static'):
    rows=[read(p) for p in OUT.glob('*.exit.json')]
    result={k:sum(r['charged_seconds'] for r in rows if r['kind']==k) for k in ('static','unittest')}
    result['static']+=reg['registration_charged_seconds']
    if (OUT/'revision_01.json').exists():result['static']+=read(OUT/'revision_01.json')['registration_charged_seconds']
    result[kind]+=extra;return result
def prerequisites(action,rev):
    preceding=list(PHASES[:PHASES.index(action)])
    expected=['unittest','discovery',*preceding]
    assert sorted(p.name for p in OUT.glob('*.exit.json'))==sorted(n+'.exit.json' for n in expected)
    held=pins([OUT/'unittest.exit.json',OUT/'discovery.exit.json',OUT/'revision_01.json'])
    for name in preceding:
        p=OUT/(name+'.exit.json');r=read(p)
        assert r['accepted'] is True and r['label']==name and r['revision_pin']==pin((OUT/'revision_01.json').read_bytes())
        assert r['helper_pins']==rev['helper_pins'] and r['source_epoch']==rev['source_epoch']
        for path,expected_pin in r['produced_and_control_pins'].items():assert pin(Path(path).read_bytes())==expected_pin,path
        held.update(pins([p]))
    return held

def register():
    started=time.perf_counter(); target=OUT/'revision_01.json';assert not target.exists()
    try:
        reg=original();mutable={str(p) for p in (CORE,PARENT,PROBE)}
        for path,expected in reg['input_pins'].items():
            if path not in mutable:assert pin(Path(path).read_bytes())==expected,path
        helpers=[CORE,PARENT,PROBE,TEST,OUT/'driver.py',Path(__file__).absolute()]
        deltas={}
        for p in (CORE,PARENT,PROBE):
            old=reg['helper_pins'][str(p)];before=(OUT/('code_'+old['sha256']+'.snapshot')).read_bytes();after=p.read_bytes()
            assert pin(before)==old
            deltas[str(p)]=''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='registered',tofile='repair'))
        # Reviewed exact delta is separately pinned before this registration executes.
        delta_path=OUT/'repair_delta.json';assert pin(delta_path.read_bytes())['sha256']==DELTA_SHA and read(delta_path)==deltas
        parent=load(PARENT,'repair_parent_register');assert parent.source()==reg['source_pins']
        code=parent.transport();assert len(code)<=29000
        helper_pins=pins(helpers)
        for p in helpers:
            raw=p.read_bytes();dest=OUT/('code_'+pin(raw)['sha256']+'.snapshot')
            if dest.exists():assert dest.read_bytes()==raw
            else:
                with dest.open('xb') as f:f.write(raw)
        with (OUT/'transport_repair.snapshot').open('xb') as f:f.write(code)
        fixed=set(Path(p) for p in reg['input_pins'] if p not in mutable)
        fixed.update(p for p in OUT.iterdir() if p.is_file())
        fixed.update(helpers+[REPAIR_SCOPE])
        inputs=pins(sorted(fixed));charge=time.perf_counter()-started
        assert reg['registration_charged_seconds']+charge<=3
        current=spent(reg,charge);assert current['static']<=50 and current['unittest']<=30 and sum(current.values())<=80
        record=dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',input_pins=inputs,helper_pins=helper_pins,
            registration_pin=pin((OUT/'registration.json').read_bytes()),registration_charged_seconds=charge,
            original_failure_pin=pin((OUT/'discovery.exit.json').read_bytes()),delta_pin=pin(delta_path.read_bytes()),
            source_epoch=reg['source_epoch'],source_pins=reg['source_pins'],transport_pin=pin(code),unit_nodes=reg['unit_nodes'],
            caps=reg['caps'],phase_caps=dict(unittest_repair=12,discovery_repair=5,profile_admission=2,probes=30,saved=8),
            prior_not_accepted_count=13,actual_F=False,run_authority=False,resource_admission=False,formal_result=False,production_seal=False)
        save(target,record);print(canonical(dict(accepted=True,registration_charged_seconds=charge,transport_pin=pin(code))).decode())
    except BaseException as error:
        save(OUT/'revision_01_failure.json',dict(accepted=False,kind='static',charged_seconds=time.perf_counter()-started,error=repr(error),actual_F=False,run_authority=False))
        raise

def unit_child():
    import unittest
    rev=read(OUT/'revision_01.json');check(rev);module=load(TEST,'pre_entry_tests');suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    def nodes(s):return [n for c in s for n in nodes(c)] if isinstance(s,unittest.TestSuite) else [s.id()]
    actual=sorted(nodes(suite));assert actual==rev['unit_nodes']
    save(OUT/'unittest_repair_admission.json',dict(nodes=actual,helper_pins=rev['helper_pins'],before_test_calls=True))
    admission=pin((OUT/'unittest_repair_admission.json').read_bytes());r=unittest.TextTestRunner(verbosity=1).run(suite)
    check(rev);assert admission==pin((OUT/'unittest_repair_admission.json').read_bytes())
    report=dict(accepted=r.wasSuccessful() and r.testsRun==len(actual) and not r.skipped,nodes=actual,tests_run=r.testsRun,failures=len(r.failures),errors=len(r.errors),skipped=len(r.skipped),admission_pin=admission)
    save(OUT/'unittest_repair_report.json',report)
    if not report['accepted']:raise SystemExit(1)
    print(canonical(dict(accepted=True,unit_nodes=len(actual))).decode())

def saved_child():
    rev=read(OUT/'revision_01.json');check(rev);held=prerequisites('saved',rev);admission=read(OUT/'profile_admission.json')
    assert admission['profile_pin']==pin((OUT/'startup_profile.json').read_bytes()) and admission['transport_pin']==rev['transport_pin']
    rows={}
    for case in ['discovery_repair',*CASES]:
        p=OUT/('probe_'+case+'.receipt.json');r=read(p)
        assert r['accepted'] is True and r['case']==case and r['transport_pin']==rev['transport_pin']
        assert r['parent_process_handle_closed'] and r['stdin_closed'] and r['writer_thread_terminal'] and not r['cleanup']
        for flag in ('actual_F','formal_result','run_authority','resource_admission','production_seal'):assert r[flag] is False
        rows[p.name]=pin(p.read_bytes())
    save(OUT/'saved_report.json',dict(accepted=True,receipt_pins=rows,profile_admission_pin=pin((OUT/'profile_admission.json').read_bytes()),predecessor_pins=held,
        original_failure_pin=rev['original_failure_pin'],no_bootstrap_or_scientific_rerun=True,actual_F=False,formal_result=False,resource_admission=False,run_authority=False))
    check(rev);assert held==prerequisites('saved',rev);print(canonical(dict(accepted=True,saved_receipts=len(rows))).decode())

def run(action):
    started=time.perf_counter();target=OUT/(action+'.exit.json');assert not target.exists()
    rev=read(OUT/'revision_01.json');reg=read(OUT/'registration.json');cap=rev['phase_caps'][action];kind='unittest' if action=='unittest_repair' else 'static'
    accepted=False;error=None;held=None;streams=None;results=[];control=pin((OUT/'revision_01.json').read_bytes())
    try:
        assert rev['accepted'] is True;check(rev);held=prerequisites(action,rev)
        cost=spent(reg,cap,kind);assert cost[kind]<=reg['caps'][kind] and sum(cost.values())<=80
        parent=load(PARENT,'repair_pre_entry_parent');assert pin(parent.transport())==rev['transport_pin']
        if action in ('unittest_repair','saved'):
            capture=load(CAPTURE,'repair_capture');label='unit_child' if action=='unittest_repair' else 'saved_child'
            rc,out,err,why,obs=capture.bounded([EXE,'-B','-s',str(Path(__file__).absolute()),label],cap-(time.perf_counter()-started)-0.7)
            streams=dict(returncode=rc,stdout_raw_base64=base64.b64encode(out).decode(),stderr_raw_base64=base64.b64encode(err).decode(),stdout_pin=pin(out),stderr_pin=pin(err),error=why,process_observation=obs)
            drain=obs['bounded_drain'];assert rc==0 and why is None and obs['handle_closed'] and not obs['cleanup']
            assert drain['reader_threads_terminal'] and drain['pipes_closed'] and not drain['reader_errors'] and not drain['cleanup'] and not drain['stdout_truncated'] and not drain['stderr_truncated']
            assert read(OUT/(action+'_report.json'))['accepted'] is True
        elif action=='discovery_repair':
            result=parent.one_case('discovery_repair',cap-(time.perf_counter()-started));results.append(result);assert result['accepted']
        elif action=='profile_admission':
            discovery=read(OUT/'probe_discovery_repair.receipt.json');assert discovery['accepted'] is True
            profile=read(OUT/'startup_profile.json');assert profile['bootstrap_pin']==rev['transport_pin']
            for path,value in profile['disk_file_observations'].items():assert pin(Path(path).read_bytes())==value
            save(OUT/'profile_admission.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',profile_pin=pin((OUT/'startup_profile.json').read_bytes()),
                transport_pin=rev['transport_pin'],helper_pins=rev['helper_pins'],environment_pin=pin(canonical(parent.environment())),
                discovery_receipt_pin=pin((OUT/'probe_discovery_repair.receipt.json').read_bytes()),registration_pin=rev['registration_pin'],revision_pin=control,
                original_failure_pin=rev['original_failure_pin'],actual_F=False,run_authority=False,resource_admission=False,formal_result=False))
        elif action=='probes':
            admission_pin=pin((OUT/'profile_admission.json').read_bytes())
            for case in CASES:
                remaining=cap-(time.perf_counter()-started)-0.7;requested=1.5 if case=='timeout' else 3
                assert remaining>=requested,'no full case budget; do not launch'
                result=parent.one_case(case,requested);results.append(result);assert result['accepted'],case
                check(rev);assert admission_pin==pin((OUT/'profile_admission.json').read_bytes())
        else:raise ValueError('fixed repair action')
        check(rev);assert control==pin((OUT/'revision_01.json').read_bytes()) and held==prerequisites(action,rev);accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)[:160]
    charge=time.perf_counter()-started;cost=spent(reg,charge,kind);previous=reg['predecessor_charged_seconds']
    accepted=accepted and charge<=cap and cost[kind]<=reg['caps'][kind] and sum(cost.values())<=80
    artifacts=pins(p for p in OUT.iterdir() if p.is_file() and p.name not in ('driver.py','repair_driver.py') and not p.name.startswith('code_'))
    record=dict(accepted=accepted,label=action,kind=kind,charged_seconds=charge,cap_seconds=cap,charged_seconds_by_kind=cost,
        all_cumulative_charged_seconds=dict(static=previous['static']+cost['static'],pytest=previous['pytest'],unittest=previous['unittest']+cost['unittest']),
        revision_pin=control,registration_pin=rev['registration_pin'],source_epoch=rev['source_epoch'],helper_pins=rev['helper_pins'],predecessor_pins=held,produced_and_control_pins=artifacts,
        error=error,streams=streams,case_receipt_pins={v['case']:pin((OUT/('probe_'+v['case']+'.receipt.json')).read_bytes()) for v in results},
        actual_F=False,run_authority=False,resource_admission=False,formal_result=False,production_seal=False,
        charge_scope='parent preparation through postchecks; editor/review/Git and final exit serialization excluded',storage_before_exit=usage())
    fits=usage()['files']+1<=64 and usage()['bytes']+len(canonical(record))+128<=8*1024**2
    record['storage_cap_satisfied']=fits;record['accepted']=accepted=accepted and fits;save(target,record)
    print(canonical(dict(accepted=accepted,label=action,charged_seconds=charge,error=error)).decode())
    if not accepted:raise SystemExit(1)

if __name__=='__main__':
    if sys.argv[1:]==['register']:register()
    elif sys.argv[1:]==['unit_child']:unit_child()
    elif sys.argv[1:]==['saved_child']:saved_child()
    elif len(sys.argv)==2 and sys.argv[1] in PHASES:run(sys.argv[1])
    else:raise SystemExit('fixed pre-entry repair checks only')
