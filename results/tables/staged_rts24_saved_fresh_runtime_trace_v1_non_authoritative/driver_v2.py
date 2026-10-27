"""Two-child, pre-import timing diagnostic. No model, adapter import or solver."""
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time

OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_runtime_guard_v1_non_authoritative'
PARENT=ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v5.py'
CORE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v8.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v4.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_runtime_trace_scope_v1.md'
PHASES=('discovery','profile_admission','pre_import','saved')
CAPS=dict(discovery=4,profile_admission=2,pre_import=4,saved=2)
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(p):return json.loads(p.read_bytes())
def save(p,v):
    with p.open('xb') as f:f.write(canonical(v))
def pins(paths):return {str(p):pin(p.read_bytes()) for p in paths}
def load(p):
    spec=importlib.util.spec_from_file_location('_trace_parent',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def previous():
    reg=read(OLD/'registration.json');failed=read(OLD/'import_discovery.exit.json');row=read(OLD/'probe_import_discovery.receipt.json')
    assert failed['accepted'] is False and row['accepted'] is False and row['bounded_drain']['killed']
    assert row['parent_process_handle_closed'] and row['stdin_closed'] and row['writer_thread_terminal'] and not row['cleanup']
    assert row['stdout_pin']==row['stderr_pin']==pin(b'')
    for path,value in {**reg['input_pins'],**failed['produced_and_control_pins']}.items():assert pin(Path(path).read_bytes())==value,path
    assert read(OLD/'unittest_report.json')['tests_run']==27 and read(OLD/'unittest.exit.json')['accepted']
    return reg,failed
def check(reg):
    previous()
    for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
def spent(extra=0):
    value=read(OUT/'registration.json')['registration_charged_seconds']
    return value+read(OUT/'registration_failure.json')['charged_seconds']+read(OUT/'compression_profile.json')['charged_seconds']+sum(read(p)['charged_seconds'] for p in OUT.glob('*.exit.json'))+extra
def storage(extra=b''):
    paths=[p for p in OUT.iterdir() if p.is_file()]
    return len(paths)+(1 if extra else 0)<=20 and sum(p.stat().st_size for p in paths)+len(extra)<=4*1024**2
def prereq(action,reg):
    required=PHASES[:PHASES.index(action)]
    assert {p.name for p in OUT.glob('*.exit.json')}=={name+'.exit.json' for name in required}
    for name in required:
        row=read(OUT/(name+'.exit.json'));assert row['accepted'] and row['registration_pin']==pin((OUT/'registration.json').read_bytes())
        for path,value in row['artifact_pins'].items():assert pin(Path(path).read_bytes())==value,path
def register():
    started=time.perf_counter();assert not (OUT/'registration.json').exists()
    old,failed=previous();parent=load(PARENT);source=parent.source();assert source==old['source_pins']
    helpers=[CORE,PROBE,PARENT,Path(__file__).absolute()];helper_pins=pins(helpers)
    save(OUT/'helper_snapshots_v2.json',{str(p):base64.b64encode(p.read_bytes()).decode() for p in helpers})
    code=parent.transport()
    import subprocess
    command=[str(parent.EXE),'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(OUT/'probe_import_discovery.plan.json'),'0'*64]
    units=len(subprocess.list2cmdline(command).encode('utf-16-le'))//2;assert units<=30000
    with (OUT/'transport.snapshot').open('xb') as f:f.write(code)
    paths={Path(p) for p in old['input_pins']};paths.update(p for p in OLD.iterdir() if p.is_file());paths.update(helpers+[SCOPE,ROOT/'docs/plan/staged_deliverability_c_saved_fresh_runtime_trace_command_repair_v1.md',OUT/'import_policy.json',OUT/'helper_snapshots_v2.json',OUT/'transport.snapshot',OUT/'registration_failure.json',OUT/'compression_profile.json',OUT/'helper_snapshots.json',OUT/'driver.py'])
    inputs=pins(sorted(paths));cost=time.perf_counter()-started;assert cost+read(OUT/'registration_failure.json')['charged_seconds']+read(OUT/'compression_profile.json')['charged_seconds']<=2
    save(OUT/'registration.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',input_pins=inputs,helper_pins=helper_pins,
        transport_pin=pin(code),command_utf16_units=units,source_epoch=old['source_epoch'],source_pins=source,
        registration_charged_seconds=cost,predecessor_charged_seconds=failed['all_cumulative_charged_seconds'],prior_not_accepted_count=18,
        caps=dict(static=16,total=16,files=20,bytes=4*1024**2,cold_children=2,adapter_imports=0),actual_F=False,run_authority=False,formal_result=False))
    print(canonical(dict(accepted=True,charge=cost,command_utf16_units=units)).decode())
def run(action):
    started=time.perf_counter();target=OUT/(action+'.exit.json');assert not target.exists();reg=read(OUT/'registration.json')
    cap=CAPS[action];accepted=False;error=None;case=None
    try:
        check(reg);prereq(action,reg);assert spent(cap)<=16
        parent=load(PARENT);assert pin(parent.transport())==reg['transport_pin']
        if action in ('discovery','pre_import'):
            case=parent.one_case('discovery' if action=='discovery' else 'import_discovery',cap-(time.perf_counter()-started))
            assert case['accepted']
        elif action=='profile_admission':
            receipt=read(OUT/'probe_discovery.receipt.json');assert receipt['accepted']
            profile=read(OUT/'startup_profile.json');assert profile['bootstrap_pin']==reg['transport_pin']
            for name,value in profile['disk_file_observations'].items():assert pin(Path(name).read_bytes())==value
            save(OUT/'profile_admission.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',profile_pin=pin((OUT/'startup_profile.json').read_bytes()),
                transport_pin=reg['transport_pin'],helper_pins=reg['helper_pins'],environment_pin=pin(canonical(parent.environment())),
                registration_pin=pin((OUT/'registration.json').read_bytes()),discovery_receipt_pin=pin((OUT/'probe_discovery.receipt.json').read_bytes()),actual_F=False,run_authority=False))
        else:
            receipt=read(OUT/'probe_import_discovery.receipt.json');assert receipt['accepted'] and receipt['result']['adapter_import_attempts']==0
            save(OUT/'saved_report.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',metadata_only=True,
                terminal_step=receipt['result']['phase_trace'][-1],diagnostic_stop_expected=True,adapter_import_attempts=0,actual_F=False,run_authority=False,formal_result=False))
        check(reg);prereq(action,reg);accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)[:160]
    charge=time.perf_counter()-started;total=spent(charge);accepted=accepted and charge<=cap and total<=16
    previous=reg['predecessor_charged_seconds'];cumulative={**previous,'static':previous['static']+total}
    record=dict(accepted=accepted,label=action,kind='static',charged_seconds=charge,cap_seconds=cap,total_charged_seconds=total,error=error,
        registration_pin=pin((OUT/'registration.json').read_bytes()),artifact_pins=pins(p for p in OUT.iterdir() if p.is_file()),
        all_cumulative_charged_seconds=cumulative,case_accepted=None if case is None else case['accepted'],prior_not_accepted_count=18,
        authority='DRAFT_NONAUTHORITATIVE',actual_F=False,run_authority=False,formal_result=False,resource_admission=False)
    raw=canonical(record);assert storage(raw)
    with target.open('xb') as f:f.write(raw)
    print(canonical(dict(accepted=accepted,label=action,charged_seconds=charge,error=error)).decode())
    if not accepted:raise SystemExit(1)
if __name__=='__main__':
    if sys.argv[1:]==['register']:
        began=time.perf_counter()
        try:register()
        except BaseException as error:
            save(OUT/'registration_failure_v2.json',dict(accepted=False,kind='static',charged_seconds=time.perf_counter()-began,error=repr(error),actual_F=False,run_authority=False))
            raise
    elif len(sys.argv)==2 and sys.argv[1] in PHASES:run(sys.argv[1])
    else:raise SystemExit('fixed pre-import diagnostic only')
