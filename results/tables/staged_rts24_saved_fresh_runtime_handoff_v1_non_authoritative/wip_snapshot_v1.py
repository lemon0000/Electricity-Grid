"""Metadata/pin checkpoint only; never imports a helper or launches a child."""
import base64
from hashlib import sha256
import json
from pathlib import Path
import time

OUT=Path(__file__).absolute().parent
ROOT=OUT.parents[2]
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def main():
    started=time.perf_counter();target=OUT/'wip_snapshot.json';assert not target.exists()
    base=read(OUT/'registration.json');repair=read(OUT/'repair_registration.json')
    checked={**base['input_pins'],**repair['input_pins']}
    for path,expected in checked.items():assert pin(Path(path).read_bytes())==expected,path
    for name in ('helper_snapshots.json','repair_helper_snapshots.json'):
        for path,encoded in read(OUT/name).items():assert base64.b64decode(encoded,validate=True)==Path(path).read_bytes(),path
    assert pin((OUT/'transport.snapshot').read_bytes())==base['transport_pin']
    assert pin((OUT/'transport_repair.snapshot').read_bytes())==repair['transport_pin']
    assert len(base['source_pins'])==49 and base['source_pins']==repair['source_pins']
    assert pin(canonical(base['source_pins']))['sha256']==base['source_epoch']==repair['source_epoch']
    for name,expected in base['source_pins'].items():assert pin((ROOT/name).read_bytes())==expected,name
    failed=read(OUT/'unittest.exit.json');passed=read(OUT/'unittest_repair.exit.json');unit=read(OUT/'unittest_repair_report.json')
    assert failed['accepted'] is False and failed['streams']['error']=='timeout'
    assert base64.b64decode(failed['streams']['stderr_raw_base64'],validate=True)==b'.'*15
    assert passed['accepted'] is True and passed['streams']['returncode']==0 and passed['streams']['error'] is None
    assert unit['accepted'] is True and unit['tests_run']==20 and unit['nodes']==repair['unit_nodes']
    assert unit['failures']==unit['errors']==unit['skipped']==0
    for record in (failed,passed):
        streams=record['streams'];observation=streams['process_observation'];drain=observation['bounded_drain']
        assert observation['handle_closed'] and not observation['cleanup']
        assert drain['reader_threads_terminal'] and drain['pipes_closed'] and not drain['cleanup'] and not drain['reader_errors']
        for label in ('stdout','stderr'):
            raw=base64.b64decode(streams[label+'_raw_base64'],validate=True);assert pin(raw)==streams[label+'_pin']
        for path,expected in record['produced_and_control_pins'].items():assert pin(Path(path).read_bytes())==expected,path
    assert not any((OUT/name).exists() for name in ('discovery.exit.json','probe_discovery.plan.json','profile_admission.json','import_discovery.exit.json','probe_cases.receipts.jsonl','saved.exit.json'))
    findings=read(OUT/'pre_seal_open_findings.json');assert findings['cold_launch_admitted'] is False and len(findings['must_fix'])==3
    inputs={str(p):pin(p.read_bytes()) for p in OUT.iterdir() if p.is_file()}
    elapsed=time.perf_counter()-started
    static=base['registration_charged_seconds']+repair['registration_charged_seconds']+elapsed
    unit_charge=failed['charged_seconds']+passed['charged_seconds']
    assert elapsed<=3 and static<=75 and unit_charge<=35 and static+unit_charge<=110
    previous=base['predecessor_charged_seconds'];cumulative=dict(static=previous['static']+static,pytest=previous['pytest'],unittest=previous['unittest']+unit_charge)
    report=dict(schema='staged_saved_F_runtime_handoff_WIP_snapshot_v1',authority='DRAFT_NONAUTHORITATIVE',
        accepted=True,acceptance_scope='metadata_and_preserved_bytes_only',status='WIP_PRE_SEAL_OPEN',checked_input_pins=len(checked),
        input_and_artifact_pins=inputs,source_epoch=base['source_epoch'],source49_unchanged=True,
        unittest_complete=20,unittest_failures=0,unittest_errors=0,unittest_skipped=0,original_unittest_timeout_preserved=True,
        prior_not_accepted_count=16,cold_children_launched=0,runtime_native_handoff_observed=False,B_S_import_observed=False,
        must_fix_count=3,charged_seconds=elapsed,cap_seconds=3,kind='static',
        scope_charged_seconds=dict(static=static,unittest=unit_charge,total=static+unit_charge),
        all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),
        cold_launch_admitted=False,official_review=False,production_seal=False,full_runtime_binding_verified=False,
        full_P1_content_verified=False,role_bootstrap=False,permit_issued=False,native_authorized=False,F_launch_admitted=False,
        actual_F=False,run_authority=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False,
        charge_scope='metadata check through pre-report bookend; startup/final serialization/editor/review/Git excluded')
    encoded=canonical(report);files=[p for p in OUT.iterdir() if p.is_file()]
    assert len(files)+1<=40 and sum(p.stat().st_size for p in files)+len(encoded)<=8*1024**2
    with target.open('xb') as stream:stream.write(encoded)
    print(canonical(dict(accepted=True,status=report['status'],scope=report['scope_charged_seconds'],cumulative_total=report['all_cumulative_total_seconds'],must_fix_count=3)).decode())
if __name__=='__main__':main()
