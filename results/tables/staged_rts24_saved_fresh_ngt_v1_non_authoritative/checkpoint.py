"""Post-saved metadata checkpoint, not a rerun or workflow admission."""
import base64
from hashlib import sha256
import json
from pathlib import Path
import time
OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
CACHE=ROOT/'results/tables/staged_rts24_saved_fresh_namespace_code_cache_v1_non_authoritative'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(p):return json.loads(p.read_bytes())
def main():
    began=time.perf_counter();reg=read(OUT/'registration.json');exit=read(OUT/'saved.exit.json');assert exit['accepted']
    for path,value in {**reg['input_pins'],**exit['artifact_pins']}.items():assert pin(Path(path).read_bytes())==value,path
    for root in (OUT,CACHE):
        for path,encoded in read(root/'helper_snapshots.json').items():assert Path(path).read_bytes()==base64.b64decode(encoded,validate=True)
    rejected=read(CACHE/'rejection_snapshot.json');assert rejected['candidate_adopted'] is False
    row=read(OUT/'probe_import_discovery.receipt.json');child=row['result']['child_record'];assert row['accepted'] and row['child_exit']==1 and not row['bounded_drain']['killed']
    assert child['primary']['message']=='diagnostic_stop_before_adapter' and child['self_handles_closed'] and child['close_calls']==[1,1]
    assert child['runtime_is_resource_owner'] and child['old_inputs_successor_matches'] and child['old_namespace_successor_matches']
    assert child['runtime_phase']=='UNRESOLVED' and child['resource_phase']=='CLOSED' and child['boundary_report']['audit_handoff_observed']==1
    assert row['parent_process_handle_closed'] and row['stdin_closed'] and row['writer_thread_terminal'] and not row['cleanup']
    for label in ('stdout','stderr'):assert pin(base64.b64decode(row[label+'_raw_base64'],validate=True))==row[label+'_pin']
    source=reg['source_pins'];assert len(source)==49 and pin(canonical(source))['sha256']==reg['source_epoch']
    for path,value in source.items():assert pin((ROOT/path).read_bytes())==value,path
    timing=read(OUT/'saved_report.json');durations=timing['graph_durations'];assert len(durations)==16 and not timing['incomplete_graph']
    cost=time.perf_counter()-began;assert cost<=2
    cumulative=dict(exit['all_cumulative_charged_seconds']);cumulative['static']+=cost
    usage=dict(exit['scope_charged_seconds']);usage['static']+=cost;assert usage['static']<=20 and usage['unittest']<=4 and sum(usage.values())<=24
    roots={name:{p.name:pin(p.read_bytes()) for p in root.iterdir() if p.is_file()} for name,root in (('cache_candidate',CACHE),('ngt_before_checkpoint',OUT))}
    report=dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',acceptance_scope='metadata_and_preserved_diagnostic_evidence_only',kind='static',charged_seconds=cost,cap_seconds=2,
        root_maps=roots,unit_complete=6,cache_candidate_adopted=False,prior_not_accepted_count=21,source_epoch=reg['source_epoch'],scope_charged_seconds=usage,
        all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),graph_completed=16,
        outer_graph_seconds_sum=sum(durations),outer_graph_seconds_min=min(durations),outer_graph_seconds_max=max(durations),
        timing_boundary='Includes enter serialization/write/flush and held function construction/reader; excludes exit output. Not pure reader CPU.',
        pre_import_parent_charge=row['charged_seconds'],self_close_witness_present=True,self_handles_close_calls=[1,1],adapter_import_attempts=0,
        cold_import_acceptance_complete=False,actual_F=False,run_authority=False,formal_result=False,resource_admission=False,scientific_evidence_adopted=False,production_seal=False)
    encoded=canonical(report);paths=[p for p in OUT.iterdir() if p.is_file()];assert len(paths)+1<=24 and sum(p.stat().st_size for p in paths)+len(encoded)<=4*1024**2
    with (OUT/'checkpoint.json').open('xb') as f:f.write(encoded)
    print(canonical(dict(accepted=True,charge=cost,scope=usage,cumulative=cumulative,total=sum(cumulative.values()))).decode())
if __name__=='__main__':main()
