"""Create-only, <=1s metadata checkpoint within the AOC2 22/8/30s caps."""
import ast
import base64
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import time
import tokenize
import zlib

ROOT=Path(__file__).absolute().parents[1]
OUT=ROOT/'results/tables/staged_rts24_saved_fresh_aoc_v4_non_authoritative'

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main():
    started=time.perf_counter();target=OUT/'checkpoint.json';assert not target.exists()
    preseal=read(OUT/'pre_seal_findings.json')
    assert pin(Path(__file__).read_bytes())==preseal['checkpoint_script_pin']
    driver=load(OUT/'driver.py','_rti_checkpoint_driver');reg=read(OUT/'registration.json');driver.check(reg)
    rows=[read(OUT/(name+'.exit.json')) for name in driver.PHASES];assert all(row['accepted'] for row in rows)
    for row in rows:
        assert row['registration_pin']==pin((OUT/'registration.json').read_bytes())
        for path,value in row['artifact_pins'].items():assert pin(Path(path).read_bytes())==value,path
    unit=read(OUT/'unittest_report.json');assert unit==dict(accepted=True,errors=0,failures=0,skipped=0,tests_run=14)
    parent=load(driver.PARENT,'_rti_checkpoint_parent');assert parent.source()==reg['source_pins']
    code=(OUT/'transport.snapshot').read_bytes();assert pin(code)==reg['transport_pin'] and parent.transport()==code
    marker=b'\nimport os as _bootstrap_os\n';assert code.count(marker)==1
    prefix=code.partition(marker)[0]
    calls=[node for node in ast.walk(ast.parse(code)) if type(node) is ast.Call and type(node.func) is ast.Attribute and node.func.attr=='b85decode'];assert len(calls)==1
    decoder=zlib.decompressobj(zdict=prefix);payload=decoder.decompress(base64.b85decode(calls[0].args[0].value),131073)
    assert len(payload)<=131072 and decoder.eof and not decoder.unconsumed_tail and not decoder.unused_data
    original=parent.CORE.read_bytes()+b'\n'+parent.PROBE.read_bytes();original=b'import builtins\n'+original.split(b'\nimport builtins\n',1)[1]
    assert original.isascii() and payload.isascii() and len(payload)==len(original)
    offsets=[];offset=0
    for line in original.splitlines(keepends=True):offsets.append(offset);offset+=len(line)
    allowed=set()
    for token in tokenize.tokenize(io.BytesIO(original).readline):
        if token.type==tokenize.COMMENT:
            assert token.start[0]==token.end[0]
            allowed.update(range(offsets[token.start[0]-1]+token.start[1],offsets[token.end[0]-1]+token.end[1]))
    assert all(current==(32 if index in allowed else original[index]) for index,current in enumerate(payload))
    receipt=read(OUT/'probe_import_discovery.receipt.json');assert receipt['accepted']
    stdout=base64.b64decode(receipt['stdout_raw_base64']);stderr=base64.b64decode(receipt['stderr_raw_base64'])
    assert pin(stdout)==receipt['stdout_pin'] and pin(stderr)==receipt['stderr_pin']
    diagnostic=parent.parse_diagnostic_stderr(stderr);assert diagnostic==receipt['result']['diagnostic']
    drain=receipt['bounded_drain'];assert drain['pipes_closed'] and drain['reader_threads_terminal'] and not drain['reader_errors'] and not drain['cleanup']
    assert not drain['stdout_truncated'] and not drain['stderr_truncated'] and receipt['parent_process_handle_closed'] and receipt['writer_thread_terminal'] and receipt['stdin_closed']
    stages=diagnostic['stages'];residual=base64.b64decode(diagnostic['non_stage_raw_base64'])
    assert pin(residual)==diagnostic['non_stage_pin']
    root_map={p.name:pin(p.read_bytes()) for p in OUT.iterdir() if p.is_file()}
    usage=dict(static=read(OUT/'size_admission.json')['charged_seconds']+reg['registration_charged_seconds']+sum(row['charged_seconds'] for row in rows if row['kind']=='static'),unittest=sum(row['charged_seconds'] for row in rows if row['kind']=='unittest'))
    charge=time.perf_counter()-started;usage['static']+=charge
    accepted=charge<=1 and usage['static']<=22 and usage['unittest']<=8 and sum(usage.values())<=30
    previous=reg['predecessor_charged_seconds'];cumulative={**previous,'static':previous['static']+usage['static'],'unittest':previous['unittest']+usage['unittest']}
    report=dict(accepted=accepted,authority='DRAFT_NONAUTHORITATIVE',kind='static',charged_seconds=charge,cap_seconds=1,
        acceptance_scope='metadata_integrity_and_partial_import_diagnostic_only',root_map_before_checkpoint=root_map,
        checkpoint_script_pin=pin(Path(__file__).read_bytes()),checkpoint_prerun_pin_matched=True,registration_pin=pin((OUT/'registration.json').read_bytes()),
        scope_charged_seconds=usage,all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),prior_not_accepted_count=25+(not accepted),
        source_epoch=reg['source_epoch'],unit_tests=14,current_payload_direct_byte_equality=True,payload_pin=pin(payload),
        command_utf16_units=reg['command_utf16_units'],stages=stages,stack_present=diagnostic['stack_present'],stage_parse_complete=False,
        adapter_import_return_observed=receipt['result']['adapter_import_return_observed'],adapter_import_attempts_upper_bound=1,
        adapter_import_call_observed_in_stack=b'in diagnostic_import_once' in residual and b'in import_module' in residual,
        sample_in_cache_path_check=b'in _check_cache' in residual and b'in is_relative_to' in residual,
        watchdog_stack_has_ellipsis=b'\n  ...\n' in residual,raw_stderr_pin=pin(stderr),non_stage_pin=pin(residual),
        parent_import_charge=receipt['charged_seconds'],parent_import_cap=receipt['cap_seconds'],child_killed=drain['killed'],
        child_record_present=receipt['result']['child_record'] is not None,child_self_close_witness_present=receipt['result']['self_close_witness_present'],
        child_self_close_state='unknown' if receipt['result']['child_record'] is None else 'observed_closed' if receipt['result']['self_close_witness_present'] else 'not_proved',
        census_helper_used_in_diagnostic=True,census_frames=diagnostic['census_frames'],census_bytes=diagnostic['census_bytes'],
        prefix_complete=receipt['result']['prefix_complete'],census_terminal_reason=receipt['result']['census_terminal_reason'],
        unreported_tail_unknown=receipt['result']['child_record'] is None,watchdog_used=False,cache_candidate_adopted=False,
        cold_import_acceptance_complete=False,full_runtime_binding_verified=False,native_behavior_verified=False,
        actual_F=False,run_authority=False,production_seal=False,formal_result=False,scientific_evidence_adopted=False,resource_admission=False)
    raw=canonical(report);assert len(root_map)+1<=26 and sum(value['bytes'] for value in root_map.values())+len(raw)<=4*1024**2
    with target.open('xb') as stream:stream.write(raw)
    print(canonical(dict(accepted=accepted,charge=charge,scope=usage,cumulative=cumulative,total=sum(cumulative.values()),files=len(root_map)+1)).decode())
    if not accepted:raise SystemExit(1)

if __name__=='__main__':main()
