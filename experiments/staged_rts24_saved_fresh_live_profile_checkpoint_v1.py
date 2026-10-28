"""Create-only checkpoint for packed finite2048; cumulative caps are never reset."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import time
import zlib

ROOT=Path(__file__).absolute().parents[1]
OUT=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v10_non_authoritative'


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def verified_saved_replay(driver,parent,receipt,row):
    saved=driver.reopen(row['embedded_artifacts'])['report'];replay=driver.saved_report(parent,receipt)
    assert canonical(saved)==canonical(replay),'complete saved replay differs'
    return replay


def main():
    started=time.perf_counter();target=OUT/'checkpoint.json';assert not target.exists()
    driver=load(OUT/'driver.py','_packed_checkpoint_driver')
    size=read(OUT/'size_admission.json');reg=read(OUT/'registration.json') if (OUT/'registration.json').exists() else None
    if 'phase_timings' in size:driver.validate_size_timings(size)
    old,prior=driver.check(reg) if reg is not None and reg['accepted'] else driver.previous()
    for row in (size,reg):
        if row is not None:
            for path,value in row.get('input_pins',{}).items():assert pin(Path(path).read_bytes())==value,path
    assert pin(Path(__file__).read_bytes())==size['input_pins'][str(Path(__file__).absolute())]
    rows={name:read(OUT/(name+'.exit.json')) for name in driver.PHASES if (OUT/(name+'.exit.json')).exists()}
    records=[size,*([reg] if reg is not None else []),*rows.values()]
    failures=[row for row in records if row['accepted'] is False]
    for name,row in rows.items():
        for path,value in row['path_artifact_pins'].items():assert pin(Path(path).read_bytes())==value,path
        driver.reopen(row['embedded_artifacts'])
        assert row['registration_pin']==pin((OUT/'registration.json').read_bytes())
        if name=='unittest':driver.unit_payload(row,reg)
        if name=='saved' and 'proposed_derived_report_pin' in row:
            parent=load(driver.PARENT,'_packed_rejected_saved_parent')
            replay=driver.saved_report(parent,read(OUT/'probe_normal.receipt.json'))
            assert pin(canonical(replay))==row['proposed_derived_report_pin']
        if row['accepted']:driver.verify_exit(name,reg)
    diagnostic_accepted=not failures and set(rows)==set(driver.PHASES)
    details={}
    if diagnostic_accepted:
        parent=load(driver.PARENT,'_packed_checkpoint_parent');assert parent.source()==reg['source_pins']
        embedded=driver.reopen(reg['embedded_artifacts']);code=embedded['transport'];assert code==parent.transport()
        marker=b'\nimport os as _bootstrap_os\n';assert code.count(marker)==1;prefix=code.partition(marker)[0]
        calls=[n for n in ast.walk(ast.parse(code)) if type(n) is ast.Call and type(n.func) is ast.Attribute and n.func.attr=='b85decode'];assert len(calls)==1
        decoder=zlib.decompressobj(zdict=prefix);payload=decoder.decompress(base64.b85decode(calls[0].args[0].value),131073)
        assert len(payload)<=131072 and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
        assert pin(payload)==size['payload_pin'] and pin(prefix)==size['dictionary_pin']
        receipt=read(OUT/'probe_normal.receipt.json');validation=driver.audit_matrix(parent,receipt)
        replay=verified_saved_replay(driver,parent,receipt,rows['saved']);saved=replay
        assert saved['diagnostic_accepted'] and saved['audit_validation']==validation
        findings=driver.reopen(rows['pre_seal']['embedded_artifacts'])['findings'];assert findings['checkpoint_script_pin']==pin(Path(__file__).read_bytes())
        stdout=base64.b64decode(receipt['stdout_raw_base64'],validate=True);stderr=base64.b64decode(receipt['stderr_raw_base64'],validate=True)
        assert pin(stdout)==receipt['stdout_pin'] and pin(stderr)==receipt['stderr_pin']
        diagnostic=parent.POST.parse(parent,stderr);assert diagnostic==receipt['result']['diagnostic']
        drain=receipt['bounded_drain'];assert drain['pipes_closed'] and drain['reader_threads_terminal'] and not drain['reader_errors'] and not drain['cleanup']
        assert not drain['stdout_truncated'] and not drain['stderr_truncated'] and not drain['killed']
        assert receipt['parent_process_handle_closed'] and receipt['writer_thread_terminal'] and receipt['stdin_closed']
        details=dict(audit_validation=validation,command_utf16_units=reg['command_utf16_units'],payload_pin=pin(payload),dictionary_pin=pin(prefix),
            unit_tests=25,stages=diagnostic['stages'],census_frames=diagnostic['census_frames'],census_bytes=diagnostic['census_bytes'],
            post_return_terminal_complete=receipt['result']['post_return_terminal_complete'],prefix_complete=receipt['result']['prefix_complete'],
            adapter_import_return_observed=receipt['result']['adapter_import_return_observed'],census_terminal_reason=receipt['result']['census_terminal_reason'],
            memory_observation=receipt['memory_observation'],memory_guard=receipt['bounded_drain']['memory_guard'],memory_observation_source=receipt['memory_observation_source'],parent_import_charge=receipt['charged_seconds'],parent_import_cap=receipt['cap_seconds'],
            raw_stdout_pin=pin(stdout),raw_stderr_pin=pin(stderr),child_self_close_witness_present=receipt['result']['self_close_witness_present'],
            child_self_close_state='observed_closed',child_killed=False,drain_reason=receipt['drain_reason'],cold_import_acceptance_complete=False,
            adapter_import_attempts_upper_bound=1,runtime_phase_before_close=receipt['result']['child_record']['runtime_phase_before_close'],post_metrics=receipt['result']['child_record']['post_metrics'],import_profile_pin=replay['import_profile_pin'],expected_import_profile_pin=replay['expected_import_profile_pin'],frozen_nfc9_import_profile_exact_match=replay['frozen_nfc9_import_profile_exact_match'],reference_source=replay['reference_source'],reference_context_pin=replay['reference_context_pin'])
    else:assert failures
    usage=dict(static=sum(row['charged_seconds'] if 'charged_seconds' in row else row['registration_charged_seconds'] for row in records if row.get('kind','static')=='static'),
        unittest=sum(row['charged_seconds'] for row in rows.values() if row['kind']=='unittest'))
    root_map={p.name:pin(p.read_bytes()) for p in OUT.iterdir() if p.is_file()}
    charge=time.perf_counter()-started;usage['static']+=charge
    accepted=charge<=driver.CHECKPOINT_CAP and usage['static']<=driver.STATIC_CAP and usage['unittest']<=driver.UNIT_CAP and sum(usage.values())<=driver.TOTAL_CAP
    previous=prior['all_cumulative_charged_seconds'];cumulative={**previous,'static':previous['static']+usage['static'],'unittest':previous['unittest']+usage['unittest']}
    package_charge=sum(usage.values());assert package_charge<=driver.TOTAL_CAP
    report=dict(accepted=accepted,authority=driver.AUTHORITY,acceptance_scope='packed_metadata_and_profile_matched_live_diagnostic_only' if diagnostic_accepted else 'rejection_metadata_only',
        diagnostic_accepted=diagnostic_accepted,kind='static',charged_seconds=charge,cap_seconds=driver.CHECKPOINT_CAP,scope_charged_seconds=usage,
        all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),package_charged_seconds=package_charge,
        prior_closed_package_charged_seconds=prior['package_charged_seconds'],
        prior_not_accepted_count=38+len(failures)+(not accepted),root_map_before_checkpoint=root_map,checkpoint_script_pin=pin(Path(__file__).read_bytes()),
        executed_input_bytes_verified=True,checkpoint_prerun_pin_matched=True,source_epoch=old['source_epoch'],
        prior_archive_files=105,prior_archive_bytes=8636628,all_unselected_events_verified=False,candidate_adopted=False,
        **details,**driver.flags())
    raw=canonical(report);assert len(root_map)+1<=driver.MAX_FILES and sum(value['bytes'] for value in root_map.values())+len(raw)<=driver.MAX_BYTES
    driver.write_raw(target,raw)
    print(canonical(dict(accepted=accepted,diagnostic_accepted=diagnostic_accepted,charge=charge,scope=usage,total=sum(cumulative.values()),package_charge=package_charge,not_accepted=report['prior_not_accepted_count'],files=len(root_map)+1)).decode())
    if not accepted:raise SystemExit(1)


if __name__=='__main__':main()
