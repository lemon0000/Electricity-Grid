"""Two-second metadata-only checkpoint for guard and stack diagnostics."""
import base64
from hashlib import sha256
import json
from pathlib import Path
import time

OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
NAMES=('runtime_guard','runtime_trace','runtime_stack','runtime_stk')
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(p):return json.loads(p.read_bytes())
def main():
    started=time.perf_counter();target=OUT/'snapshot.json';assert not target.exists()
    roots={name:ROOT/('results/tables/staged_rts24_saved_fresh_'+name+'_v1_non_authoritative') for name in NAMES}
    checked={};maps={};costs={}
    for name,root in roots.items():
        rows={p.name:pin(p.read_bytes()) for p in root.iterdir() if p.is_file()};maps[name]=rows
        costs[name]=dict(static=0.0,unittest=0.0)
        for p in root.glob('*.json'):
            row=read(p)
            if p.name.startswith('helper_snapshots'):
                for path,encoded in row.items():assert base64.b64decode(encoded,validate=True)==Path(path).read_bytes(),path
                continue
            if type(row) is not dict:continue
            for field in ('input_pins','produced_and_control_pins','artifact_pins'):
                for path,value in row.get(field,{}).items():
                    assert path not in checked or checked[path]==value,path
                    checked[path]=value
            if p.name=='registration.json':costs[name]['static']+=row['registration_charged_seconds']
            elif p.name in ('registration_failure.json','registration_failure_v2.json','compression_profile.json'):
                costs[name]['static']+=row['charged_seconds']
            elif p.name.endswith('.exit.json'):costs[name][row['kind']]+=row['charged_seconds']
    for path,value in checked.items():assert pin(Path(path).read_bytes())==value,path
    guard=roots['runtime_guard'];unit=read(guard/'unittest_report.json');assert unit['accepted'] and unit['tests_run']==27 and unit['failures']==unit['errors']==unit['skipped']==0
    failed=read(guard/'probe_import_discovery.receipt.json');assert not failed['accepted'] and failed['bounded_drain']['killed'] and failed['stdout_pin']==failed['stderr_pin']==pin(b'')
    assert all((roots['runtime_trace']/name).exists() for name in ('registration_failure.json','registration_failure_v2.json','compression_profile.json'))
    early=read(roots['runtime_stack']/'probe_import_discovery.receipt.json');early_record=json.loads(base64.b64decode(early['stdout_raw_base64'],validate=True))
    assert not early['accepted'] and early_record['failure_phase']=='SELF' and early_record['guard']['source_open_attempts']==0
    assert early_record['primary']['message']=='conditional TCB profile mismatch; local lease refused'
    stk=roots['runtime_stk'];sample=read(stk/'probe_import_discovery.receipt.json');assert sample['accepted'] and sample['bounded_drain']['killed']
    raw=base64.b64decode(sample['stderr_raw_base64'],validate=True);assert pin(raw)==sample['stderr_pin'] and b'verify_runtime_namespace' in raw and b'open_bootstrap_import_boundary' in raw
    assert sample['result']['child_record'] is None and sample['result']['self_close_witness_present'] is False and read(stk/'saved.exit.json')['accepted']
    for row in (failed,early,sample):
        assert row['parent_process_handle_closed'] and row['stdin_closed'] and row['writer_thread_terminal'] and not row['cleanup']
        assert row['bounded_drain']['pipes_closed'] and row['bounded_drain']['reader_threads_terminal'] and not row['bounded_drain']['cleanup']
        for name in ('stdout','stderr'):assert pin(base64.b64decode(row[name+'_raw_base64'],validate=True))==row[name+'_pin']
    base=read(guard/'registration.json')['predecessor_charged_seconds'];source=read(guard/'registration.json')['source_pins']
    assert len(source)==49
    for path,value in source.items():assert pin((ROOT/path).read_bytes())==value,path
    elapsed=time.perf_counter()-started;assert elapsed<=2
    cumulative=dict(base)
    for value in costs.values():
        for key,cost in value.items():cumulative[key]+=cost
    cumulative['static']+=elapsed
    report=dict(schema='staged_saved_F_guard_stack_checkpoint_v1',authority='DRAFT_NONAUTHORITATIVE',accepted=True,
        acceptance_scope='preserved_bytes_metadata_and_report_consistency_only',checked_input_pins=len(checked),root_maps=maps,
        roots_usage={name:dict(files=len(rows),bytes=sum(p['bytes'] for p in rows.values()),map_pin=pin(canonical(rows))) for name,rows in maps.items()},
        scope_charges=costs,charged_seconds=elapsed,cap_seconds=2,kind='static',all_cumulative_charged_seconds=cumulative,
        all_cumulative_total_seconds=sum(cumulative.values()),prior_not_accepted_count=20,source_epoch=pin(canonical(source))['sha256'],
        unit_complete=27,three_pre_seal_findings_closed=True,cold_import_acceptance_complete=False,stack_sample_pin=pin(raw),
        stack_inference='One-second sample is in namespace graph verification inside the B_S factory before adapter import; it does not prove the entire original timeout stayed there.',
        child_self_close_witness_present=False,no_scientific_rerun=True,actual_F=False,run_authority=False,formal_result=False,
        resource_admission=False,scientific_evidence_adopted=False,production_seal=False,full_runtime_binding_verified=False)
    encoded=canonical(report);assert len(encoded)+Path(__file__).stat().st_size<=1024**2
    with target.open('xb') as f:f.write(encoded)
    print(canonical(dict(accepted=True,charge=elapsed,checked=len(checked),scope_charges=costs,cumulative=cumulative,total=sum(cumulative.values()),usage=report['roots_usage'])).decode())
if __name__=='__main__':main()
