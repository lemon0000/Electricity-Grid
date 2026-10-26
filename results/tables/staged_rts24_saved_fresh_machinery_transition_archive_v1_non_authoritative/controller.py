"""Read-only mechanical successor; old implementation helper bytes remain frozen."""
import time
STARTED=time.perf_counter()
import base64
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
def save(name,value):
    with (BASE/name).open('xb') as stream:stream.write(raw(value))
def fixed(registration,action,produced=False):
    assert action in ('saved','terminal')
    actual={p.relative_to(ROOT).as_posix() for p in (ROOT/registration['old_root_path']).rglob('*') if p.is_file()}
    assert actual==set(registration['old_root_pins']) and len(actual)==44
    assert dict(files=len(actual),bytes=sum((ROOT/n).stat().st_size for n in actual))==registration['old_root_usage']
    expected={'controller.py','registration.json'}
    if action=='terminal':expected.update(('saved_report.json','saved.exit.json'))
    if produced:expected.add(action+'_report.json')
    assert {p.relative_to(BASE).as_posix() for p in BASE.rglob('*') if p.is_file()}==expected
    assert names(ROOT/n for n in registration['old_root_pins'])==registration['old_root_pins']
    assert names(ROOT/n for n in registration['source_pins'])==registration['source_pins']
    assert pin(Path(registration['executable']).read_bytes())==registration['executable_pin']
    assert {n:pin(Path(n).read_bytes()) for n in registration['external_pins']}==registration['external_pins']
    assert pin(Path(__file__).read_bytes())==registration['controller_pin']
    assert sys.version==registration['python'] and sys.dont_write_bytecode is True and sys.flags.optimize==0
    assert Path(sys.executable).absolute()==Path(registration['executable']).absolute()
def held_module(path,expected,label):
    blob=path.read_bytes();assert pin(blob)==expected
    module=ModuleType(label);module.__file__=str(path);exec(compile(blob,str(path),'exec',dont_inherit=True),vars(module));return module
def replay_saved(registration):
    saved_raw=(BASE/'saved_report.json').read_bytes();saved=json.loads(saved_raw);row=read(BASE/'saved.exit.json')
    assert row['label']=='saved' and row['accepted'] and row['returncode']==0 and row['error'] is None
    assert row['authority']==saved['authority']=='DRAFT_NONAUTHORITATIVE' and saved['action']=='saved' and row['kind']=='static' and not row['missing_report']
    assert row['predecessor_charged_seconds']==registration['predecessor_charged_seconds'] and row['implementation_charged_before_archive']==registration['implementation_charged_before_archive']
    assert row['report_pin']==pin(saved_raw) and saved['accepted'] and row['controller_pin']==registration['controller_pin']
    assert row['registration_pin']==saved['registration_pin']==pin((BASE/'registration.json').read_bytes())
    for suffix in ('stdout','stderr'):
        blob=base64.b64decode(row[suffix+'_raw_base64'],validate=True);assert pin(blob)==row[suffix+'_pin']
        if suffix=='stderr':assert not blob
        else:assert json.loads(blob)==dict(action='saved',accepted=True)
    state=row['process_observation'];drain=state['bounded_drain']
    assert state['handle_closed'] and not state['cleanup'] and drain['reader_threads_terminal'] and drain['pipes_closed']
    assert not drain['cleanup'] and not drain['reader_errors'] and not drain['stdout_truncated'] and not drain['stderr_truncated']
    assert 0<=row['charged_seconds']<=5 and row['cap_seconds']==5
    assert row['cost_lineage_complete'] and row['tail_reserve_seconds']==.5
    expected=registration['implementation_charged_before_archive'].copy();expected['static']+=registration['registration_charged_seconds']+row['charged_seconds']
    assert row['implementation_charged_seconds']==expected and row['all_cumulative_charged_seconds']=={k:registration['predecessor_charged_seconds'][k]+expected[k] for k in expected}
    assert row['old_root_usage']==registration['old_root_usage']
    archive_use=dict(files=3,bytes=sum((BASE/n).stat().st_size for n in ('controller.py','registration.json','saved_report.json')))
    assert row['archive_usage_before_exit']==archive_use and row['combined_usage_before_exit']=={k:registration['old_root_usage'][k]+archive_use[k] for k in archive_use}
    assert saved['old_root_pins']==registration['old_root_pins']
    assert all(row[n] is saved[n] is False for n in ('actual_F','run_authority','resource_admission','formal_result','predecessor_resource_admission','production_seal','original_driver_saved_terminal_executed'))
    return saved,row
def report_readback(report,registration,action):
    assert report['accepted'] and report['authority']=='DRAFT_NONAUTHORITATIVE' and report['action']==action
    assert report['registration_pin']==pin((BASE/'registration.json').read_bytes()) and report['controller_pin']==registration['controller_pin']
    assert report['old_root_pins']==registration['old_root_pins'] and report['oracle_result_pin']==pin(raw(report['oracle_result']))
    assert report['oracle_result']['source_epoch']==sha256(raw(registration['source_pins'])).hexdigest()
    assert all(report[n] is False for n in ('actual_F','run_authority','resource_admission','formal_result','predecessor_resource_admission','production_seal','original_driver_saved_terminal_executed'))
    if action=='terminal':
        assert report['saved_report_pin']==pin((BASE/'saved_report.json').read_bytes()) and report['saved_exit_pin']==pin((BASE/'saved.exit.json').read_bytes()) and report['reopen_result_equal']
def child(action):
    assert action in ('saved','terminal')
    registration_raw=(BASE/'registration.json').read_bytes();registration=json.loads(registration_raw)
    report=dict(authority='DRAFT_NONAUTHORITATIVE',action=action,original_driver_saved_terminal_executed=False,
        actual_F=False,run_authority=False,resource_admission=False,formal_result=False,predecessor_resource_admission=False,production_seal=False)
    try:
        fixed(registration,action);path=ROOT/registration['old_oracle_path']
        oracle=held_module(path,registration['old_root_pins'][path.relative_to(ROOT).as_posix()],'held_transition_oracle')
        result=oracle.verify();fixed(registration,action)
        report.update(oracle_result=result,oracle_result_pin=pin(raw(result)),registration_pin=pin(registration_raw),controller_pin=registration['controller_pin'],old_root_pins=registration['old_root_pins'])
        if action=='terminal':
            saved,anchor=replay_saved(registration);saved_raw=(BASE/'saved_report.json').read_bytes()
            assert result==saved['oracle_result'] and pin(raw(result))==saved['oracle_result_pin']
            assert saved['registration_pin']==pin(registration_raw) and saved['old_root_pins']==registration['old_root_pins']
            report.update(saved_report_pin=pin(saved_raw),saved_exit_pin=pin((BASE/'saved.exit.json').read_bytes()),reopen_result_equal=True)
        assert (BASE/'registration.json').read_bytes()==registration_raw
        report['accepted']=True
    except BaseException as error:report.update(accepted=False,error_type=type(error).__name__)
    save(action+'_report.json',report);print(json.dumps(dict(action=action,accepted=report['accepted']),sort_keys=True))
    if not report['accepted']:raise SystemExit(1)
def parent(action):
    assert action in ('saved','terminal')
    reg_raw=(BASE/'registration.json').read_bytes();reg=json.loads(reg_raw)
    for suffix in ('_report.json','.exit.json'):assert not (BASE/(action+suffix)).exists()
    report_path=BASE/(action+'_report.json');error=None;code=None;stdout=stderr=b'';state=None;before_ok=False;saved_charge=None if action=='terminal' else 0
    try:
        if action=='terminal':
            charge=read(BASE/'saved.exit.json').get('charged_seconds')
            if type(charge) in (int,float) and 0<=charge<=10000:saved_charge=charge
        fixed(reg,action);before_ok=True
        if action=='terminal':
            saved_report,saved_exit=replay_saved(reg)
        capture_path=ROOT/reg['old_capture_path'];capture=held_module(capture_path,reg['old_root_pins'][capture_path.relative_to(ROOT).as_posix()],'held_transition_capture')
        argv=[reg['executable'],'-B','-s',str(Path(__file__).resolve()),'--child',action];launches=[]
        def audit(event,args):
            if event=='subprocess.Popen':
                assert not launches and args[0]==reg['executable'] and args[1]==subprocess.list2cmdline(argv) and str(args[2])==str(ROOT) and args[3] is None
                launches.append(True)
        sys.addaudithook(audit);timeout=5.-1.5-(time.perf_counter()-STARTED)
        code,stdout,stderr,error,state=capture.bounded(argv,timeout)
        fixed(reg,action,produced=True);assert (BASE/'registration.json').read_bytes()==reg_raw and launches==[True]
        assert state['handle_closed'] and not state['cleanup'] and state['bounded_drain']['reader_threads_terminal'] and state['bounded_drain']['pipes_closed']
        assert not state['bounded_drain']['cleanup'] and not state['bounded_drain']['reader_errors'] and not state['bounded_drain']['stdout_truncated'] and not state['bounded_drain']['stderr_truncated'] and not stderr
    except BaseException as caught:error=error or type(caught).__name__
    previous=reg['implementation_charged_before_archive'].copy();previous['static']+=reg['registration_charged_seconds']
    lineage_complete=saved_charge is not None
    if lineage_complete:previous['static']+=saved_charge
    charged=time.perf_counter()-STARTED+.5;successor={k:previous[k]+(charged if k=='static' else 0) for k in previous} if lineage_complete else None
    observed_report=None if not report_path.exists() else read(report_path)
    try:
        if observed_report is not None:report_readback(observed_report,reg,action)
    except BaseException as caught:error=error or type(caught).__name__
    accepted=lineage_complete and code==0 and error is None and before_ok and observed_report is not None and observed_report.get('accepted') and charged<=5 and successor['static']<=60 and successor['pytest']<=45 and sum(successor.values())<=105
    def usage(root):
        files=[p for p in root.rglob('*') if p.is_file()];return dict(files=len(files),bytes=sum(p.stat().st_size for p in files))
    old_use=usage(ROOT/reg['old_root_path']);own_use=usage(BASE)
    value=dict(authority='DRAFT_NONAUTHORITATIVE',label=action,kind='static',accepted=bool(accepted),returncode=code,error=error,
        report_pin=None if observed_report is None else pin(report_path.read_bytes()),missing_report=observed_report is None,registration_pin=pin(reg_raw),controller_pin=reg['controller_pin'],
        stdout_raw_base64=base64.b64encode(stdout).decode('ascii'),stderr_raw_base64=base64.b64encode(stderr).decode('ascii'),stdout_pin=pin(stdout),stderr_pin=pin(stderr),
        process_observation=state,charged_seconds=charged,cap_seconds=5,tail_reserve_seconds=.5,
        predecessor_charged_seconds=reg['predecessor_charged_seconds'],implementation_charged_before_archive=reg['implementation_charged_before_archive'],
        implementation_charged_seconds=successor,cost_lineage_complete=lineage_complete,all_cumulative_charged_seconds={k:reg['predecessor_charged_seconds'][k]+successor[k] for k in successor} if lineage_complete else None,
        old_root_usage=old_use,archive_usage_before_exit=own_use,combined_usage_before_exit={k:old_use[k]+own_use[k] for k in old_use},
        original_driver_saved_terminal_executed=False,actual_F=False,run_authority=False,resource_admission=False,formal_result=False,predecessor_resource_admission=False,production_seal=False)
    payload=raw(value)
    if old_use['files']>48 or old_use['bytes']>2*1024**2 or own_use['files']+1>16 or own_use['bytes']+len(payload)>256*1024:
        value.update(accepted=False,error='archive_resource_cap');payload=raw(value)
        assert own_use['bytes']+len(payload)<=256*1024,'failure exit exceeds registered storage cap'
    save(action+'.exit.json',value)
    print(json.dumps(dict(action=action,accepted=value['accepted'],charged_seconds=charged,implementation_charged_seconds=successor),sort_keys=True))
    if not value['accepted']:raise SystemExit(1)
if __name__=='__main__':
    if sys.argv[1:2]==['--child']:child(sys.argv[2])
    else:
        action=sys.argv[1];assert action in ('saved','terminal')
        try:parent(action)
        except BaseException as error:
            if not (BASE/(action+'.exit.json')).exists():
                save(action+'.exit.json',dict(authority='DRAFT_NONAUTHORITATIVE',label=action,kind='static',accepted=False,
                    partial_controller_failure=True,cost_lineage_complete=False,error_type=type(error).__name__,charged_seconds=time.perf_counter()-STARTED+.5,cap_seconds=5,
                    actual_F=False,run_authority=False,resource_admission=False,formal_result=False,predecessor_resource_admission=False,production_seal=False))
            raise
