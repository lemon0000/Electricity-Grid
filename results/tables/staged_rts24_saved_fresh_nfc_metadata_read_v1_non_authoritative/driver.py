"""One read-only metadata-check trace, charged to the existing finite1024 package."""
import base64
from collections import Counter
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import time
import zlib

ROOT=Path(__file__).absolute().parents[3];OUT=Path(__file__).absolute().parent
FROZEN=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v3_non_authoritative'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_metadata_read_scope_v1.md'


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def load(path):
    spec=importlib.util.spec_from_file_location('_frozen_metadata_counter',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def main():
    started=time.perf_counter();target=OUT/'inspection.json';assert not target.exists() and {p.name for p in OUT.iterdir()}=={'driver.py'}
    paths=[*FROZEN.iterdir(),Path(__file__).absolute(),SCOPE];before={str(p):pin(p.read_bytes()) for p in paths}
    prior=read(FROZEN/'checkpoint.json');assert prior['accepted'] and not prior['diagnostic_accepted'] and prior['prior_not_accepted_count']==34
    assert prior['all_cumulative_total_seconds']==775.8277461000646 and prior['original_package_charged_seconds']==13.555978000011237
    for name,value in prior['root_map_before_checkpoint'].items():assert pin((FROZEN/name).read_bytes())==value
    driver=load(FROZEN/'driver.py');reg=read(FROZEN/'registration.json')
    original=Path.read_bytes;journal=[];unique={};byte_total=0;error=None;check_charge=None
    def traced(path):
        nonlocal byte_total
        raw=original(path);absolute=str(path.absolute());value=pin(raw)
        assert len(journal)<8192 and (absolute in unique or len(unique)<2048)
        byte_total+=len(raw);assert byte_total<=1073741824
        if absolute in unique:assert unique[absolute]==value,'same-path bytes changed during metadata check'
        else:unique[absolute]=value
        journal.append([absolute,len(raw),value['sha256']]);return raw
    try:
        Path.read_bytes=traced;clock=time.perf_counter();driver.check(reg);check_charge=time.perf_counter()-clock
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)[:200]
    finally:Path.read_bytes=original
    assert Path.read_bytes is original
    raw=canonical(journal);assert len(raw)<=4194304
    compressed=zlib.compress(raw,9);decoder=zlib.decompressobj();saved=decoder.decompress(compressed,4194305)
    assert saved==raw and decoder.eof and not decoder.unconsumed_tail and not decoder.unused_data
    rows=json.loads(saved);assert canonical(rows)==saved
    counts=Counter(row[0] for row in rows);reopened={}
    for path,size,sha in rows:
        value=dict(bytes=size,sha256=sha)
        assert type(size) is int and size>=0 and len(sha)==64
        assert path not in reopened or reopened[path]==value;reopened[path]=value
    assert reopened==unique and sum(row[1] for row in rows)==byte_total
    assert {str(p):pin(p.read_bytes()) for p in paths}==before
    original_roots=[ROOT/f'results/tables/staged_rts24_saved_fresh_nfc_v{v}_non_authoritative' for v in (1,2,3)]
    old_files=[p for folder in original_roots for p in folder.iterdir()];assert len(old_files)==20 and all(p.is_file() for p in old_files)
    charge=time.perf_counter()-started;accepted=error is None and charge<=2
    cumulative={**prior['all_cumulative_charged_seconds'],'static':prior['all_cumulative_charged_seconds']['static']+charge}
    package_static=sum(read(folder/'checkpoint.json')['scope_charged_seconds']['static'] for folder in original_roots)+charge
    package_unit=sum(read(folder/'checkpoint.json')['scope_charged_seconds']['unittest'] for folder in original_roots)
    assert package_static<=22 and package_unit<=8 and package_static+package_unit<=30
    report=dict(accepted=accepted,authority='DRAFT_NONAUTHORITATIVE',acceptance_scope='explicit_Path_read_bytes_count_only',kind='static',charged_seconds=charge,cap_seconds=2,
        input_pins=before,previous_checkpoint_pin=pin((FROZEN/'checkpoint.json').read_bytes()),previous_check_accepted=error is None,
        metadata_check_seconds=check_charge,read_calls=len(journal),unique_paths=len(unique),duplicate_read_calls=len(journal)-len(unique),
        read_bytes=byte_total,unique_bytes=sum(v['bytes'] for v in unique.values()),duplicate_read_bytes=byte_total-sum(v['bytes'] for v in unique.values()),
        read_multiplicity_histogram={str(k):v for k,v in sorted(Counter(counts.values()).items())},
        largest_read_multiplicities=sorted(([count,path] for path,count in counts.items()),reverse=True)[:12],
        journal_encoding='zlib_canonical_json_then_base64',journal_raw_pin=pin(raw),journal_compressed_pin=pin(compressed),journal_zlib_base64=base64.b64encode(compressed).decode(),
        journal_saved_replay_equal=True,all_repeated_path_pins_consistent=True,path_read_bytes_restored=True,error=error,
        all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),prior_not_accepted_count=34+(not accepted),
        original_package_charged_seconds=package_static+package_unit,original_package_static_seconds=package_static,original_package_unittest_seconds=package_unit,
        old_package_files=20,new_files_including_record=2,unit_children_launched=0,cold_children_launched=0,all_unselected_events_verified=False,
        cache_candidate_adopted=False,production_helper_selected=False,**driver.flags())
    encoded=canonical(report);assert len(encoded)<=262144 and len(old_files)+2<=30
    assert sum(p.stat().st_size for p in old_files)+Path(__file__).stat().st_size+len(encoded)<=4194304
    with target.open('xb') as stream:stream.write(encoded)
    print(canonical({k:report[k] for k in ('accepted','charged_seconds','metadata_check_seconds','read_calls','unique_paths','duplicate_read_calls','read_bytes','unique_bytes','original_package_charged_seconds','all_cumulative_total_seconds')}).decode())
    if not accepted:raise SystemExit(1)


if __name__=='__main__':main()
