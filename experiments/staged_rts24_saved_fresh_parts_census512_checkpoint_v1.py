"""Create-only, <=1s metadata checkpoint within the parts512 static22/unit6/total28s caps."""
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
OUT=ROOT/'results/tables/staged_rts24_saved_fresh_pfc_v1_non_authoritative'

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def rejected(driver, started):
    old, prior = driver.previous()
    reg = read(OUT / 'registration.json') if (OUT / 'registration.json').exists() else None
    if reg is not None:
        driver.check(reg)
    records = [p for p in OUT.iterdir() if p.name.endswith('.exit.json') or p.name in ('size_admission.json', 'size_failure.json', 'registration_failure.json')]
    failures = [p for p in records if read(p)['accepted'] is False]
    assert failures
    for path in records:
        for source, value in read(path).get('artifact_pins', {}).items():
            assert pin(Path(source).read_bytes()) == value, source
    size = read(OUT / 'size_admission.json') if (OUT / 'size_admission.json').exists() else None
    if size is not None:
        for path, value in size['input_pins'].items():
            assert pin(Path(path).read_bytes()) == value, path
    usage = driver.spent() if reg is not None else dict(static=sum((read(p)['charged_seconds'] for p in records)), unittest=0.0)
    root_map = {p.name: pin(p.read_bytes()) for p in OUT.iterdir() if p.is_file()}
    unit_count = None if not (OUT / 'unittest_report.json').exists() else read(OUT / 'unittest_report.json')['tests_run']
    charge = time.perf_counter() - started
    usage['static'] += charge
    accepted = charge <= 1 and usage['static'] <= 22 and (usage['unittest'] <= 6)
    previous = prior['all_cumulative_charged_seconds']
    cumulative = {**previous, 'static': previous['static'] + usage['static'], 'unittest': previous['unittest'] + usage['unittest']}
    report = dict(accepted=accepted, authority='DRAFT_NONAUTHORITATIVE', acceptance_scope='rejection_metadata_only', diagnostic_accepted=False, kind='static', charged_seconds=charge, cap_seconds=1, scope_charged_seconds=usage, all_cumulative_charged_seconds=cumulative, all_cumulative_total_seconds=sum(cumulative.values()), prior_not_accepted_count=30 + len(failures) + (not accepted), root_map_before_checkpoint=root_map, rejection_record_pins={p.name: pin(p.read_bytes()) for p in failures}, checkpoint_script_pin=pin(Path(__file__).read_bytes()), checkpoint_prerun_pin_matched=size is not None, executed_input_bytes_verified=size is not None, source_epoch=old['source_epoch'], unit_tests=unit_count, unit_tests_planned=8, all_unselected_events_verified=False, candidate_adopted=False, actual_F=False, run_authority=False, production_seal=False, formal_result=False, scientific_evidence_adopted=False, resource_admission=False)
    raw = canonical(report)
    assert len(root_map) + 1 <= 30 and sum((v['bytes'] for v in root_map.values())) + len(raw) <= 4 * 1024 ** 2
    driver.write_raw(OUT / 'checkpoint.json', raw)
    print(canonical(dict(accepted=accepted, diagnostic_accepted=False, charge=charge, scope=usage, total=sum(cumulative.values()), not_accepted=report['prior_not_accepted_count'])).decode())
    if not accepted:
        raise SystemExit(1)

def main():
    started=time.perf_counter();target=OUT/'checkpoint.json';assert not target.exists()
    driver=load(OUT/'driver.py','_rti_checkpoint_driver')
    if (OUT/'pre_seal_findings.json').exists():assert pin(Path(__file__).read_bytes())==read(OUT/'pre_seal_findings.json')['checkpoint_script_pin']
    elif (OUT/'size_admission.json').exists():assert pin(Path(__file__).read_bytes())==read(OUT/'size_admission.json')['input_pins'][str(Path(__file__).absolute())]
    paths=[OUT/(name+'.exit.json') for name in driver.PHASES]
    if not all(p.exists() and read(p)['accepted'] for p in paths):return rejected(driver,started)
    reg=read(OUT/'registration.json');driver.check(reg)
    rows=[read(OUT/(name+'.exit.json')) for name in driver.PHASES];assert all(row['accepted'] for row in rows)
    for row in rows:
        assert row['registration_pin']==pin((OUT/'registration.json').read_bytes())
        for path,value in row['artifact_pins'].items():assert pin(Path(path).read_bytes())==value,path
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
    receipt=read(OUT/'probe_import_discovery.receipt.json');assert receipt['accepted'];audit_validation=driver.audit_matrix(parent,receipt)
    saved=read(OUT/'saved_report.json');assert saved['diagnostic_accepted'] and saved['audit_validation']==audit_validation
    stdout=base64.b64decode(receipt['stdout_raw_base64']);stderr=base64.b64decode(receipt['stderr_raw_base64'])
    assert pin(stdout)==receipt['stdout_pin'] and pin(stderr)==receipt['stderr_pin']
    diagnostic=parent.validate_prefix_stderr(stderr);assert diagnostic==receipt['result']['diagnostic']
    drain=receipt['bounded_drain'];assert drain['pipes_closed'] and drain['reader_threads_terminal'] and not drain['reader_errors'] and not drain['cleanup']
    assert not drain['stdout_truncated'] and not drain['stderr_truncated'] and receipt['parent_process_handle_closed'] and receipt['writer_thread_terminal'] and receipt['stdin_closed']
    stages=diagnostic['stages'];residual=base64.b64decode(diagnostic['non_stage_raw_base64'])
    assert pin(residual)==diagnostic['non_stage_pin']
    root_map={p.name:pin(p.read_bytes()) for p in OUT.iterdir() if p.is_file()}
    usage=dict(static=read(OUT/'size_admission.json')['charged_seconds']+reg['registration_charged_seconds']+sum(row['charged_seconds'] for row in rows if row['kind']=='static'),unittest=sum(row['charged_seconds'] for row in rows if row['kind']=='unittest'))
    unit=read(OUT/'unittest_report.json');assert unit==dict(accepted=True,tests_run=8,failures=0,errors=0,skipped=0)
    charge=time.perf_counter()-started;usage['static']+=charge
    accepted=charge<=1 and usage['static']<=22 and usage['unittest']<=6 and sum(usage.values())<=28
    previous=reg['predecessor_charged_seconds'];cumulative={**previous,'static':previous['static']+usage['static'],'unittest':previous['unittest']+usage['unittest']}
    report=dict(accepted=accepted,authority='DRAFT_NONAUTHORITATIVE',kind='static',charged_seconds=charge,cap_seconds=1,
        acceptance_scope='metadata_integrity_and_partial_import_diagnostic_only',diagnostic_accepted=True,root_map_before_checkpoint=root_map,
        checkpoint_script_pin=pin(Path(__file__).read_bytes()),checkpoint_prerun_pin_matched=True,registration_pin=pin((OUT/'registration.json').read_bytes()),
        scope_charged_seconds=usage,all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),prior_not_accepted_count=30+(not accepted),
        source_epoch=reg['source_epoch'],unit_tests=8,prior_unit_tests_reused=dict(image_pin=9,census=14,terminal=4),audit_validation=audit_validation,all_unselected_events_verified=False,candidate_adopted=False,current_payload_direct_byte_equality=True,payload_pin=pin(payload),
        command_utf16_units=reg['command_utf16_units'],stages=stages,stack_present=diagnostic['stack_present'],stage_parse_complete=False,
        adapter_import_return_observed=receipt['result']['adapter_import_return_observed'],adapter_import_attempts_upper_bound=1,
        adapter_import_call_observed_in_stack=b'in diagnostic_import_once' in residual and b'in import_module' in residual,
        sample_in_cache_path_check=b'in _check_cache' in residual and b'in is_relative_to' in residual,
        watchdog_stack_has_ellipsis=b'\n  ...\n' in residual,raw_stderr_pin=pin(stderr),non_stage_pin=pin(residual),
        memory_observation=receipt['memory_observation'],drain_reason=receipt['drain_reason'],parent_import_charge=receipt['charged_seconds'],parent_import_cap=receipt['cap_seconds'],child_killed=drain['killed'],
        child_record_present=receipt['result']['child_record'] is not None,child_self_close_witness_present=receipt['result']['self_close_witness_present'],
        child_self_close_state='unknown' if receipt['result']['child_record'] is None else 'observed_closed' if receipt['result']['self_close_witness_present'] else 'not_proved',
        census_helper_used_in_diagnostic=True,census_frames=diagnostic['census_frames'],census_bytes=diagnostic['census_bytes'],
        finite_terminal_complete=receipt['result']['finite_terminal_complete'],prefix_complete=receipt['result']['prefix_complete'],census_terminal_reason=receipt['result']['census_terminal_reason'],
        unreported_tail_unknown=receipt['result']['child_record'] is None,watchdog_used=False,cache_candidate_adopted=False,
        cold_import_acceptance_complete=False,full_runtime_binding_verified=False,native_behavior_verified=False,
        actual_F=False,run_authority=False,production_seal=False,formal_result=False,scientific_evidence_adopted=False,resource_admission=False)
    raw=canonical(report);assert len(root_map)+1<=30 and sum(value['bytes'] for value in root_map.values())+len(raw)<=4*1024**2
    driver.write_raw(target,raw)
    print(canonical(dict(accepted=accepted,charge=charge,scope=usage,cumulative=cumulative,total=sum(cumulative.values()),files=len(root_map)+1)).decode())
    if not accepted:raise SystemExit(1)

if __name__=='__main__':main()
