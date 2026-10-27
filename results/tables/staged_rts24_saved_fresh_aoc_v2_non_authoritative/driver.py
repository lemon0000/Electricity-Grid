"""Fixed selected-open guard census in a bounded child."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time
OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_rci_v1_non_authoritative'
FAILED=ROOT/'results/tables/staged_rts24_saved_fresh_aoc_v1_non_authoritative'
CORE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v16.py'
HELPER=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_census_v2.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v13.py'
PARENT=ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v13.py'
TEST=ROOT/'tests/test_staged_rts24_saved_fresh_audit_census_v2.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_audit_census_scope_v2.md'
CAPTURE=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/capture.py'
EXE='D:/Miniconda3/envs/compute/python.exe'
PHASES=('unittest','pre_seal','discovery','profile_admission','audit_prefix','saved')
CAPS=dict(unittest=8,pre_seal=1,discovery=3,profile_admission=1,audit_prefix=8,saved=2)
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(p):return json.loads(p.read_bytes())
def save(p,v):
    with p.open('xb') as f:f.write(canonical(v))
def pins(paths):return {str(p):pin(p.read_bytes()) for p in paths}
def load(p,name='_ngt_parent'):
    spec=importlib.util.spec_from_file_location(name,p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def previous():
    reg=read(OLD/'registration.json');report=read(OLD/'checkpoint.json')
    assert report['accepted'] and report['prior_not_accepted_count']==22 and report['all_cumulative_total_seconds']==638.752948900011
    for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    for name,value in report['root_map_before_checkpoint'].items():assert pin((OLD/name).read_bytes())==value,name
    script=ROOT/'experiments/staged_rts24_saved_fresh_runtime_import_timing_checkpoint_v2.py'
    assert pin(script.read_bytes())==report['checkpoint_script_pin']==read(OLD/'pre_seal_findings.json')['checkpoint_script_pin']
    rejection=read(FAILED/'rejection_snapshot.json');assert rejection['accepted'] and rejection['prior_not_accepted_count']==23
    for name,value in rejection['root_map_before_snapshot'].items():assert pin((FAILED/name).read_bytes())==value,name
    for path,value in read(FAILED/'helper_snapshots.json').items():assert Path(path).read_bytes()==base64.b64decode(value),path
    return reg,rejection
def check(reg):
    previous()
    for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
def spent(extra=0,kind='static'):
    result=dict(static=read(OUT/'registration.json')['registration_charged_seconds']+read(OUT/'size_admission.json')['charged_seconds'],unittest=0.0)
    for p in OUT.glob('*.exit.json'):
        row=read(p);result[row['kind']]+=row['charged_seconds']
    result[kind]+=extra;return result
def prereq(action,reg):
    required=PHASES[:PHASES.index(action)];assert {p.name for p in OUT.glob('*.exit.json')}=={name+'.exit.json' for name in required}
    for name in required:
        row=read(OUT/(name+'.exit.json'));assert row['accepted'] and row['registration_pin']==pin((OUT/'registration.json').read_bytes())
        for path,value in row['artifact_pins'].items():assert pin(Path(path).read_bytes())==value,path
def register():
    started=time.perf_counter();assert not (OUT/'registration.json').exists();old,prior=previous();parent=load(PARENT);assert parent.source()==old['source_pins']
    size=read(OUT/'size_admission.json');assert size['accepted'] and size['command_utf16_units']<=30000
    for path,value in size['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    helpers=[CORE,HELPER,PROBE,PARENT,TEST,Path(__file__).absolute()]
    save(OUT/'helper_snapshots.json',{str(p):base64.b64encode(p.read_bytes()).decode() for p in helpers})
    code=parent.transport()
    import subprocess
    command=[EXE,'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(OUT/'probe_import_discovery.plan.json'),'0'*64]
    units=len(subprocess.list2cmdline(command).encode('utf-16-le'))//2
    with (OUT/'transport.snapshot').open('xb') as f:f.write(code)
    save(OUT/'command_size.json',dict(command_utf16_units=units,transport_pin=pin(code),cap=30000,before_spawn=True,actual_F=False,run_authority=False))
    assert units<=30000
    tree=ast.parse(TEST.read_bytes());cls=next(n for n in tree.body if type(n) is ast.ClassDef and n.name=='CensusTests')
    nodes=['census_tests.CensusTests.'+n.name for n in cls.body if type(n) is ast.FunctionDef and n.name.startswith('test_')]
    legacy=next(n for n in tree.body if type(n) is ast.Assign and any(type(t) is ast.Name and t.id=='LEGACY_NODES' for t in n.targets))
    nodes=sorted(nodes+['_census_legacy.RuntimeHandoffTests.'+name for name in ast.literal_eval(legacy.value)]);assert len(nodes)==14
    paths={Path(p) for p in old['input_pins']}
    for root in (OLD,FAILED):paths.update(p for p in root.iterdir() if p.is_file())
    paths.update(ROOT/path for path in ('tests/test_staged_rts24_saved_fresh_runtime_handoff_v3.py','experiments/staged_rts24_saved_fresh_pre_entry_lease_v7.py','experiments/staged_rts24_saved_fresh_entry_namespace_v2.py'))
    paths.update(helpers+[SCOPE,OUT/'size_admission.json',OUT/'helper_snapshots.json',OUT/'transport.snapshot',OUT/'command_size.json',OUT/'import_policy.json'])
    inputs=pins(sorted(paths));cost=time.perf_counter()-started;assert cost<=2
    save(OUT/'registration.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',input_pins=inputs,helper_pins=pins(helpers),unit_nodes=nodes,
        transport_pin=pin(code),command_utf16_units=units,source_pins=old['source_pins'],source_epoch=old['source_epoch'],
        registration_charged_seconds=cost,predecessor_charged_seconds=prior['all_cumulative_charged_seconds'],prior_not_accepted_count=23,cache_candidate_adopted=False,
        caps=dict(static=22,unittest=8,total=30,files=26,bytes=4*1024**2),actual_F=False,run_authority=False))
    print(canonical(dict(accepted=True,charge=cost,units=units,nodes=len(nodes))).decode())
def unit_child():
    import unittest
    reg=read(OUT/'registration.json');check(reg);module=load(TEST,'census_tests');suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    def nodes(s):return [n for c in s for n in nodes(c)] if isinstance(s,unittest.TestSuite) else [s.id()]
    actual=sorted(nodes(suite));assert actual==reg['unit_nodes'];save(OUT/'unittest_admission.json',dict(nodes=actual,before_test_calls=True))
    result=unittest.TextTestRunner(verbosity=1).run(suite);check(reg)
    report=dict(accepted=result.wasSuccessful() and result.testsRun==len(actual) and not result.skipped,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped))
    save(OUT/'unittest_report.json',report)
    if not report['accepted']:raise SystemExit(1)
def run(action):
    started=time.perf_counter();target=OUT/(action+'.exit.json');assert not target.exists();reg=read(OUT/'registration.json');cap=CAPS[action];kind='unittest' if action=='unittest' else 'static'
    accepted=False;error=None;streams=None;case=None
    try:
        check(reg);prereq(action,reg);budget=spent(cap,kind);assert budget[kind]<=reg['caps'][kind] and sum(budget.values())<=30
        parent=load(PARENT);assert pin(parent.transport())==reg['transport_pin']
        if action=='unittest':
            capture=load(CAPTURE,'_ngt_capture');rc,out,err,why,obs=capture.bounded([EXE,'-B','-s',str(Path(__file__).absolute()),'unit_child'],cap-(time.perf_counter()-started)-.7)
            streams=dict(returncode=rc,error=why,stdout_pin=pin(out),stderr_pin=pin(err),stdout_raw_base64=base64.b64encode(out).decode(),stderr_raw_base64=base64.b64encode(err).decode(),process_observation=obs)
            assert rc==0 and why is None and obs['handle_closed'] and not obs['cleanup']
            drain=obs['bounded_drain'];assert drain['pipes_closed'] and drain['reader_threads_terminal'] and not drain['reader_errors'] and not drain['cleanup'] and not drain['stdout_truncated'] and not drain['stderr_truncated']
            assert read(OUT/'unittest_report.json')['accepted']
        elif action=='pre_seal':
            summary=read(OUT/'pre_seal_findings.json');assert summary['must_fix_open']==[] and summary['helper_pins']==reg['helper_pins'] and summary['official_review'] is False
            save(OUT/'pre_seal_admission.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',diagnostic_only=True,summary_pin=pin((OUT/'pre_seal_findings.json').read_bytes()),actual_F=False,run_authority=False))
        elif action in ('discovery','audit_prefix'):
            case=parent.one_case('discovery' if action=='discovery' else 'import_discovery',cap-(time.perf_counter()-started));assert case['accepted']
        elif action=='profile_admission':
            profile=read(OUT/'startup_profile.json');assert profile['bootstrap_pin']==reg['transport_pin']
            for path,value in profile['disk_file_observations'].items():assert pin(Path(path).read_bytes())==value,path
            save(OUT/'profile_admission.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',profile_pin=pin((OUT/'startup_profile.json').read_bytes()),transport_pin=reg['transport_pin'],helper_pins=reg['helper_pins'],
                environment_pin=pin(canonical(parent.environment())),registration_pin=pin((OUT/'registration.json').read_bytes()),discovery_receipt_pin=pin((OUT/'probe_discovery.receipt.json').read_bytes()),actual_F=False,run_authority=False))
        else:
            row=read(OUT/'probe_import_discovery.receipt.json');assert row['accepted'];diagnostic=row['result']['diagnostic'];child=row['result']['child_record']
            save(OUT/'saved_report.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',metadata_only=True,stages=diagnostic['stages'],graph_frames=diagnostic['graph_frames'],
                census_frames=diagnostic['census_frames'],census_bytes=diagnostic['census_bytes'],prefix_complete=row['result']['prefix_complete'],
                census_terminal_reason=row['result']['census_terminal_reason'],unreported_tail_unknown=child is None,
                stack_present=diagnostic['stack_present'],non_stage_pin=diagnostic['non_stage_pin'],stage_parse_complete=False,
                child_self_close_witness_present=row['result']['self_close_witness_present'],adapter_import_attempts_upper_bound=1,
                adapter_import_return_observed=row['result']['adapter_import_return_observed'],child_status=None if child is None else child['status'],
                child_primary=None if child is None else child['primary'],actual_F=False,run_authority=False,formal_result=False,resource_admission=False))
        check(reg);prereq(action,reg);accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)[:160]
    charge=time.perf_counter()-started;usage=spent(charge,kind);accepted=accepted and charge<=cap and usage[kind]<=reg['caps'][kind] and sum(usage.values())<=30
    previous=reg['predecessor_charged_seconds'];cumulative={**previous,'static':previous['static']+usage['static'],'unittest':previous['unittest']+usage['unittest']}
    record=dict(accepted=accepted,label=action,kind=kind,charged_seconds=charge,cap_seconds=cap,scope_charged_seconds=usage,all_cumulative_charged_seconds=cumulative,
        registration_pin=pin((OUT/'registration.json').read_bytes()),artifact_pins=pins(p for p in OUT.iterdir() if p.is_file()),error=error,streams=streams,case_accepted=None if case is None else case['accepted'],authority='DRAFT_NONAUTHORITATIVE',actual_F=False,run_authority=False,formal_result=False,resource_admission=False)
    raw=canonical(record);paths=[p for p in OUT.iterdir() if p.is_file()];assert len(paths)+1<=26 and sum(p.stat().st_size for p in paths)+len(raw)<=4*1024**2
    with target.open('xb') as f:f.write(raw)
    print(canonical(dict(accepted=accepted,label=action,charge=charge,error=error)).decode())
    if not accepted:raise SystemExit(1)
def size_admission():
    import io,tokenize,subprocess,zlib
    started=time.perf_counter();target=OUT/'size_admission.json';assert not target.exists();old,prior=previous()
    paths=[CORE,HELPER,PROBE,PARENT,TEST,Path(__file__).absolute(),SCOPE,OUT/'import_policy.json']
    inputs=pins(paths);parent=load(PARENT);sources=parent.source();code=parent.transport()
    marker=b'\nimport os as _bootstrap_os\n';assert code.count(marker)==1
    prefix,separator,tail=code.partition(marker);assert prefix and separator
    original=CORE.read_bytes()+b'\n'+PROBE.read_bytes();before,body=original.split(b'\nimport builtins\n',1);intended=b'import builtins\n'+body
    lines=intended.decode().splitlines(keepends=True)
    for token in tokenize.tokenize(io.BytesIO(intended).readline):
        if token.type==tokenize.COMMENT:
            row,col=token.start;lines[row-1]=lines[row-1][:col]+' '*(token.end[1]-col)+lines[row-1][token.end[1]:]
    intended=''.join(lines).encode();node=next(n for n in ast.walk(ast.parse(code)) if type(n) is ast.Call and type(n.func) is ast.Attribute and n.func.attr=='b85decode')
    packed=base64.b85decode(node.args[0].value);decoder=zlib.decompressobj(zdict=prefix);decoded=decoder.decompress(packed,131073)
    assert decoded==intended and len(decoded)<=131072 and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
    assert [(t.type,t.string) for t in tokenize.tokenize(io.BytesIO(prefix).readline)]==[(t.type,t.string) for t in tokenize.tokenize(io.BytesIO(before).readline)]
    assert ast.dump(ast.parse(prefix))==ast.dump(ast.parse(before))
    assert ast.dump(ast.parse(decoded),include_attributes=True)==ast.dump(ast.parse(b'import builtins\n'+body),include_attributes=True)
    assert compile(decoded,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0)==compile(b'import builtins\n'+body,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0)
    argv=[EXE,'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(OUT/'probe_import_discovery.plan.json'),'0'*64]
    units=len(subprocess.list2cmdline(argv).encode('utf-16-le'))//2
    assert pins(paths)==inputs and parent.source()==sources
    charge=time.perf_counter()-started
    save(target,dict(accepted=charge<=2 and units<=30000,authority='DRAFT_NONAUTHORITATIVE',kind='static',charged_seconds=charge,cap_seconds=2,
        input_pins=inputs,prefix_before_pin=pin(before),prefix_after_pin=pin(prefix),dictionary_pin=pin(prefix),intended_payload_pin=pin(intended),decoded_payload_pin=pin(decoded),
        packed_pin=pin(packed),transport_pin=pin(code),command_utf16_units=units,payload_byte_equal=True,payload_position_ast_equal=True,payload_code_equal=True,
        prefix_tokens_equal=True,prefix_ast_equal=True,prefix_exact_code_unchanged_claimed=False,eof=decoder.eof,unused=False,unconsumed=False,
        unit_children_launched=0,cold_children_launched=0,actual_F=False,run_authority=False))
    print(canonical(dict(accepted=charge<=2 and units<=30000,charge=charge,units=units,prefix_before=len(before),prefix_after=len(prefix))).decode())
    if charge>2 or units>30000:raise SystemExit(1)

if __name__=='__main__':
    if sys.argv[1:]==['size_admission']:
        started=time.perf_counter()
        try:size_admission()
        except BaseException as error:
            if not (OUT/'size_admission.json').exists():save(OUT/'size_failure.json',dict(accepted=False,kind='static',charged_seconds=time.perf_counter()-started,error=repr(error),actual_F=False,run_authority=False))
            raise
    elif sys.argv[1:]==['register']:
        started=time.perf_counter()
        try:register()
        except BaseException as error:save(OUT/'registration_failure.json',dict(accepted=False,kind='static',charged_seconds=time.perf_counter()-started,error=repr(error),actual_F=False,run_authority=False));raise
    elif sys.argv[1:]==['unit_child']:unit_child()
    elif len(sys.argv)==2 and sys.argv[1] in PHASES:run(sys.argv[1])
    else:raise SystemExit('fixed graph timing scope')
