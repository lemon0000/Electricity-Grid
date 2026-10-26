"""Terminal-only continuation: preserve failure and repair exact addition order."""
import time
STARTED=time.perf_counter()
import ast
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
def save(name,value):
    with (BASE/name).open('xb') as stream:stream.write(raw(value))
def setup():
    revision_raw=(BASE/'revision_02.json').read_bytes();revision=json.loads(revision_raw);reg=read(BASE/'registration.json')
    return revision_raw,revision,reg
def fixed(revision,reg,produced=False):
    expected={'controller.py','registration.json','saved_report.json','saved.exit.json','terminal.exit.json','repair_controller.py','revision_02.json'}
    if produced:expected.add('terminal_repair_report.json')
    assert {p.relative_to(BASE).as_posix() for p in BASE.rglob('*') if p.is_file()}==expected
    assert all(pin((ROOT/n).read_bytes())==p for n,p in revision['preserved_pins'].items())
    assert pin(Path(__file__).read_bytes())==revision['repair_controller_pin']
    old={p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in (ROOT/reg['old_root_path']).rglob('*') if p.is_file()}
    assert old==reg['old_root_pins'] and len(old)==44
    assert all(pin((ROOT/n).read_bytes())==p for n,p in reg['source_pins'].items())
    assert pin(Path(reg['executable']).read_bytes())==reg['executable_pin'] and all(pin(Path(n).read_bytes())==p for n,p in reg['external_pins'].items())
    assert Path(sys.executable).absolute()==Path(reg['executable']).absolute() and sys.version==reg['python'] and sys.dont_write_bytecode and sys.flags.optimize==0
def corrected_original(revision):
    path=BASE/'controller.py';blob=path.read_bytes();assert pin(blob)==revision['original_controller_pin']
    before=ast.parse(blob);after=ast.parse(blob)
    fn=next(n for n in after.body if isinstance(n,ast.FunctionDef) and n.name=='replay_saved')
    needle=ast.parse("expected['static']+=registration['registration_charged_seconds']+row['charged_seconds']").body[0]
    matches=[i for i,node in enumerate(fn.body) if ast.dump(node)==ast.dump(needle)];assert len(matches)==1;i=matches[0]
    fn.body[i:i+1]=ast.parse("expected['static']+=registration['registration_charged_seconds']\nexpected['static']+=row['charged_seconds']").body
    assert [ast.dump(n) for n in before.body if getattr(n,'name',None)!='replay_saved']==[ast.dump(n) for n in after.body if getattr(n,'name',None)!='replay_saved']
    original_fn=next(n for n in before.body if getattr(n,'name',None)=='replay_saved')
    patched_fn=next(n for n in after.body if getattr(n,'name',None)=='replay_saved')
    expected=ast.parse(blob);expected_fn=next(n for n in expected.body if getattr(n,'name',None)=='replay_saved')
    expected_fn.body[i:i+1]=ast.parse("expected['static']+=registration['registration_charged_seconds']\nexpected['static']+=row['charged_seconds']").body
    assert ast.dump(expected)==ast.dump(after)
    module=ModuleType('held_archive_addition_order_revision');module.__file__=str(path)
    exec(compile(ast.fix_missing_locations(after),str(path),'exec',dont_inherit=True),vars(module))
    return module,dict(original_function_ast_pin=pin(ast.dump(original_fn).encode()),patched_function_ast_pin=pin(ast.dump(patched_fn).encode()),only_change='split static registration and saved charge additions in parent order')
def child():
    revision_raw,revision,reg=setup()
    result=dict(authority='DRAFT_NONAUTHORITATIVE',accepted=False,actual_F=False,run_authority=False,resource_admission=False,formal_result=False,predecessor_resource_admission=False,production_seal=False,original_terminal_accepted=False)
    try:
        fixed(revision,reg);module,transform=corrected_original(revision);saved,saved_exit=module.replay_saved(reg)
        failed=read(BASE/'terminal.exit.json');assert not failed['accepted'] and failed['returncode'] is None and failed['missing_report'] and failed['process_observation'] is None
        assert failed['charged_seconds']==revision['original_terminal_charge'] and failed['error']=='AssertionError'
        oracle_path=ROOT/reg['old_oracle_path'];oracle=module.held_module(oracle_path,reg['old_root_pins'][oracle_path.relative_to(ROOT).as_posix()],'held_repair_oracle')
        report=oracle.verify();assert raw(report)==raw(saved['oracle_result']);fixed(revision,reg)
        result.update(accepted=True,oracle_result=report,oracle_result_pin=pin(raw(report)),saved_report_pin=pin((BASE/'saved_report.json').read_bytes()),saved_exit_pin=pin((BASE/'saved.exit.json').read_bytes()),
            original_terminal_pin=pin((BASE/'terminal.exit.json').read_bytes()),registration_pin=pin((BASE/'registration.json').read_bytes()),revision_pin=pin(revision_raw),repair_controller_pin=revision['repair_controller_pin'],transform=transform,reopen_result_equal=True)
    except BaseException as error:result['error_type']=type(error).__name__
    save('terminal_repair_report.json',result);print(json.dumps(dict(accepted=result['accepted']),sort_keys=True))
    if not result['accepted']:raise SystemExit(1)
def parent():
    revision_raw,revision,reg=setup();error=None;code=None;stdout=stderr=b'';state=None
    try:
        fixed(revision,reg);module,transform=corrected_original(revision)
        path=ROOT/reg['old_capture_path'];capture=module.held_module(path,reg['old_root_pins'][path.relative_to(ROOT).as_posix()],'held_repair_capture')
        argv=[reg['executable'],'-B','-s',str(Path(__file__).resolve()),'--child'];launches=[]
        def audit(event,args):
            if event=='subprocess.Popen':
                assert not launches and args[0]==reg['executable'] and args[1]==subprocess.list2cmdline(argv) and str(args[2])==str(ROOT) and args[3] is None;launches.append(True)
        sys.addaudithook(audit);remaining=5.-revision['original_terminal_charge'];timeout=remaining-1.2-(time.perf_counter()-STARTED)
        code,stdout,stderr,error,state=capture.bounded(argv,timeout);fixed(revision,reg,produced=True)
        child_result=read(BASE/'terminal_repair_report.json');saved=read(BASE/'saved_report.json')
        assert child_result['accepted'] and child_result['authority']=='DRAFT_NONAUTHORITATIVE' and child_result['reopen_result_equal']
        assert raw(child_result['oracle_result'])==raw(saved['oracle_result']) and child_result['oracle_result_pin']==pin(raw(saved['oracle_result']))
        for field,name in (('saved_report_pin','saved_report.json'),('saved_exit_pin','saved.exit.json'),('original_terminal_pin','terminal.exit.json'),('registration_pin','registration.json'),('revision_pin','revision_02.json')):assert child_result[field]==pin((BASE/name).read_bytes())
        assert child_result['repair_controller_pin']==revision['repair_controller_pin'] and child_result['transform']==transform and launches==[True]
        assert all(child_result[n] is False for n in ('actual_F','run_authority','resource_admission','formal_result','predecessor_resource_admission','production_seal','original_terminal_accepted'))
        assert json.loads(stdout)==dict(accepted=True) and not stderr and state['handle_closed'] and not state['cleanup'] and state['bounded_drain']['reader_threads_terminal'] and state['bounded_drain']['pipes_closed'] and not state['bounded_drain']['cleanup'] and not state['bounded_drain']['reader_errors'] and not state['bounded_drain']['stdout_truncated'] and not state['bounded_drain']['stderr_truncated']
    except BaseException as caught:error=error or type(caught).__name__
    charged=time.perf_counter()-STARTED+.5;terminal_total=revision['original_terminal_charge']+charged
    previous=read(BASE/'terminal.exit.json')['implementation_charged_seconds'];total=previous.copy();total['static']+=revision['registration_charged_seconds'];total['static']+=charged
    accepted=code==0 and error is None and terminal_total<=5 and total['static']<=60 and total['pytest']<=45 and sum(total.values())<=105
    files=[p for p in BASE.rglob('*') if p.is_file()]
    value=dict(authority='DRAFT_NONAUTHORITATIVE',accepted=accepted,label='terminal_repair',kind='static',returncode=code,error=error,charged_seconds=charged,terminal_original_plus_repair_seconds=terminal_total,terminal_total_cap=5,
        implementation_charged_seconds=total,all_cumulative_charged_seconds={k:reg['predecessor_charged_seconds'][k]+total[k] for k in total},
        stdout_raw_base64=base64.b64encode(stdout).decode('ascii'),stderr_raw_base64=base64.b64encode(stderr).decode('ascii'),stdout_pin=pin(stdout),stderr_pin=pin(stderr),process_observation=state,
        report_pin=pin((BASE/'terminal_repair_report.json').read_bytes()) if (BASE/'terminal_repair_report.json').exists() else None,revision_pin=pin(revision_raw),old_root_pins=reg['old_root_pins'],
        archive_usage_before_exit=dict(files=len(files),bytes=sum(p.stat().st_size for p in files)),actual_F=False,run_authority=False,resource_admission=False,formal_result=False,predecessor_resource_admission=False,production_seal=False,original_terminal_accepted=False)
    if len(files)+1>16 or sum(p.stat().st_size for p in files)+len(raw(value))>256*1024:
        value.update(accepted=False,error='repair_resource_cap');assert len(files)+1<=16 and sum(p.stat().st_size for p in files)+len(raw(value))<=256*1024,'failure exit cannot fit resource cap'
    save('terminal_repair.exit.json',value);print(json.dumps(dict(accepted=value['accepted'],charged_seconds=charged,terminal_original_plus_repair_seconds=terminal_total,implementation_charged_seconds=total),sort_keys=True))
    if not value['accepted']:raise SystemExit(1)
if __name__=='__main__':
    if sys.argv[1:2]==['--child']:child()
    else:
        try:parent()
        except BaseException as error:
            if not (BASE/'terminal_repair.exit.json').exists():
                charged=time.perf_counter()-STARTED+.5
                failure=dict(authority='DRAFT_NONAUTHORITATIVE',accepted=False,partial_capture=True,error_type=type(error).__name__,charged_seconds=charged,terminal_total_cap=5,cost_lineage_complete=False,
                    terminal_original_plus_repair_seconds=None,implementation_charged_seconds=None,all_cumulative_charged_seconds=None,original_terminal_accepted=False,actual_F=False,run_authority=False,resource_admission=False,formal_result=False,predecessor_resource_admission=False,production_seal=False)
                try:
                    revision_raw,revision,reg=setup();previous=read(BASE/'terminal.exit.json')['implementation_charged_seconds'];total=previous.copy();total['static']+=revision['registration_charged_seconds'];total['static']+=charged
                    failure.update(cost_lineage_complete=True,terminal_original_plus_repair_seconds=revision['original_terminal_charge']+charged,implementation_charged_seconds=total,all_cumulative_charged_seconds={k:reg['predecessor_charged_seconds'][k]+total[k] for k in total})
                except BaseException:pass
                save('terminal_repair.exit.json',failure)
            raise
