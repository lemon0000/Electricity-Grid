"""<=1s create-only preservation after command admission failed; no child."""
import base64
from hashlib import sha256
import json
from pathlib import Path
import time

OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_rci_v1_non_authoritative'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def main():
    started=time.perf_counter();target=OUT/'rejection_snapshot.json';assert not target.exists()
    failure=read(OUT/'registration_failure.json');size=read(OUT/'command_size.json')
    assert failure['accepted'] is False and size['command_utf16_units']==30049 and size['cap']==30000
    assert pin((OUT/'transport.snapshot').read_bytes())==size['transport_pin']
    for path,value in read(OUT/'helper_snapshots.json').items():assert Path(path).read_bytes()==base64.b64decode(value),path
    prior=read(OLD/'checkpoint.json');assert prior['accepted'] and prior['prior_not_accepted_count']==22
    for name,value in prior['root_map_before_checkpoint'].items():assert pin((OLD/name).read_bytes())==value,name
    reg=read(OLD/'registration.json')
    for path,value in reg['source_pins'].items():assert pin((ROOT/path).read_bytes())==value,path
    assert not (OUT/'registration.json').exists() and not list(OUT.glob('*.exit.json'))
    inventory={path.name:pin(path.read_bytes()) for path in OUT.iterdir() if path.is_file()}
    charge=time.perf_counter()-started;scope=failure['charged_seconds']+charge
    cumulative={**prior['all_cumulative_charged_seconds'],'static':prior['all_cumulative_charged_seconds']['static']+scope}
    report=dict(accepted=charge<=1,authority='DRAFT_NONAUTHORITATIVE',kind='static',charged_seconds=charge,cap_seconds=1,
        acceptance_scope='failed_registration_preservation_only',prior_not_accepted_count=23,registration_accepted=False,
        command_utf16_units=30049,command_cap=30000,unit_children_launched=0,cold_children_launched=0,adapter_imports=0,
        root_map_before_snapshot=inventory,source_epoch=reg['source_epoch'],scope_charged_seconds=dict(static=scope,unittest=0.0),
        all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),
        open_preseal_findings=['same_creator_before_count','installation_zero_to_one','primary_cause_self_reference','exact_frame_schedule_and_monotonicity'],
        candidate_adopted=False,actual_F=False,run_authority=False,production_seal=False,formal_result=False,resource_admission=False)
    raw=canonical(report);assert len(inventory)+1<=24 and sum(value['bytes'] for value in inventory.values())+len(raw)<=4*1024**2
    with target.open('xb') as stream:stream.write(raw)
    print(canonical(dict(accepted=report['accepted'],charge=charge,scope=scope,total=sum(cumulative.values()),not_accepted=23)).decode())
    if not report['accepted']:raise SystemExit(1)
if __name__=='__main__':main()
