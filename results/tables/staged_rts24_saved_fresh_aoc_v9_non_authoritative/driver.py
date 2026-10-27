"""Fixed 256-event selected-open census with immutable admission records."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time
OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_image_pin_v1_non_authoritative'
AOC=ROOT/'results/tables/staged_rts24_saved_fresh_aoc_v5_non_authoritative'
AOC4=ROOT/'results/tables/staged_rts24_saved_fresh_aoc_v4_non_authoritative'
CORE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v24.py'
HELPER=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_census256_v1.py'
BASE_HELPER=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_image_pin_v1.py'
GRAPH=ROOT/'experiments/staged_rts24_saved_fresh_import_graph_v1.py'
TEST=ROOT/'tests/test_staged_rts24_saved_fresh_census256_v1.py'
CAPTURE=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/capture.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v21.py'
PARENT=ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v21.py'
CHECKPOINT=ROOT/'experiments/staged_rts24_saved_fresh_audit_census256_checkpoint_v1.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_prefix256_scope_v1.md'
EXE='D:/Miniconda3/envs/compute/python.exe'
PHASES=('unittest','pre_seal','discovery','profile_admission','audit_prefix','saved')
CAPS=dict(unittest=5,pre_seal=2,discovery=3,profile_admission=2,audit_prefix=8,saved=2)
_ACTIVE_EXIT=None
FILE_CAPS={'driver.py':65536,'import_policy.json':8192,'size_admission.json':262144,'helper_snapshots.json':524288,'transport.snapshot':32768,'registration.json':524288,
    'startup_profile.json':131072,'probe_discovery.plan.json':65536,'probe_import_discovery.plan.json':65536,
    'probe_discovery.receipt.json':1048576,'probe_import_discovery.receipt.json':1048576,'saved_report.json':65536,'checkpoint.json':65536}
BASE_FILES={'driver.py','import_policy.json','size_admission.json','helper_snapshots.json','transport.snapshot','command_size.json','registration.json'}
OUTPUTS=dict(unittest={'unittest_admission.json','unittest_report.json'},pre_seal={'pre_seal_admission.json'},discovery={'probe_discovery.plan.json','probe_discovery.receipt.json','startup_profile.json'},
    profile_admission={'profile_admission.json'},audit_prefix={'probe_import_discovery.plan.json','probe_import_discovery.receipt.json'},saved={'saved_report.json'})
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(p):return json.loads(p.read_bytes())
def space_for(additions):
    current={p.name:p.stat().st_size for p in OUT.iterdir() if p.is_file()}
    assert len(current)==len(list(OUT.iterdir()))
    needed=dict(additions)
    for name in ('checkpoint.json',_ACTIVE_EXIT):
        if name is not None and name not in current and name not in needed:needed[name]=FILE_CAPS.get(name,16384)
    assert not set(additions)&set(current)
    assert len(current)+len(needed)<=30 and sum(current.values())+sum(needed.values())<=4*1024**2
def write_raw(p,raw):
    assert p.parent==OUT and len(raw)<=FILE_CAPS.get(p.name,16384)
    space_for({p.name:len(raw)})
    with p.open('xb') as f:f.write(raw)
def save(p,v):write_raw(p,canonical(v))
def parent_save(p,v):
    raw=canonical(v)
    if p.name.endswith('.receipt.json') and len(raw)>FILE_CAPS[p.name]:
        reduced={**v,'accepted':False,'primary':'receipt_archive_cap','archive_prior_primary':v['primary'],
            'result':None,'archive_derived_result_pin':pin(canonical(v['result'])),'archive_proposed_receipt_pin':pin(raw)}
        write_raw(p,canonical(reduced));raise ValueError('receipt archive cap; original streams retained')
    write_raw(p,raw)
def pins(paths):return {str(p):pin(p.read_bytes()) for p in paths}
def load(p,name='_ngt_parent'):
    spec=importlib.util.spec_from_file_location(name,p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
HISTORY=((ROOT/'results/tables/staged_rts24_saved_fresh_aoc_v6_non_authoritative/checkpoint.json','831d779d34a769ded1637d29fa916817610820236fdba99655b19f9ee1e42eb0'),(ROOT/'results/tables/staged_rts24_saved_fresh_origin_order_v1_non_authoritative/inspection.json','0cc296172c80f86a3bf369788d5ca8f74494f670811e65c0a15d91c464e84ce2'),(ROOT/'results/tables/staged_rts24_saved_fresh_origin_order_v2_non_authoritative/inspection.json','5d04580e2de720cd16f66c52ea8bb868e68e5f3ff3e179a98e6d7768f8be145a'),(ROOT/'results/tables/staged_rts24_saved_fresh_aoc_v7_non_authoritative/checkpoint.json','dcb6c39c8357209d978cc1a5e5aed0040fe97fd75290252938e76e31f0919ca5'),(ROOT/'results/tables/staged_rts24_saved_fresh_aoc_v8_non_authoritative/checkpoint.json','f096ef65cd7839eb36d602a55fc3321b6180273c7c8ce0e0e0fcc906eae9601d'),(ROOT/'results/tables/staged_rts24_saved_fresh_ful_v1_non_authoritative/checkpoint.json','2706ffa0011448b064605b417aa3656a68bbef794b9575af2db082c96f410bfb'),)
def previous():
    assert sha256((OLD/'checkpoint.exit.json').read_bytes()).hexdigest()=='b839b2c46ff60993e2e7ec26859b999da3dad2991c08de3b778604fdea812edf'
    assert sha256((OLD/'registration.json').read_bytes()).hexdigest()=='ea48a47b8dbf67819738e6d31493a1aab8fa94802027ff73cf9c3283ed6d4873'
    reg=read(OLD/'registration.json');report=read(OLD/'checkpoint.exit.json')
    assert report['accepted'] and report['prior_not_accepted_count']==25 and report['all_cumulative_total_seconds']==668.4250488000209
    expected={Path(path).name for path in report['artifact_pins']}|{'checkpoint.exit.json'}
    assert {p.name for p in OLD.iterdir()}==expected
    for path,value in report['artifact_pins'].items():
        assert Path(path).parent==OLD and pin(Path(path).read_bytes())==value,path
    for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    for path,value in reg['source_pins'].items():assert pin((ROOT/path).read_bytes())==value,path
    assert read(OLD/'unittest_report.json')==dict(accepted=True,tests_run=9,failures=0,errors=0,skipped=0)
    assert read(OLD/'unittest_admission.json')['nodes']==reg['unit_nodes'] and len(reg['unit_nodes'])==9
    assert read(OLD/'metrics.json')['benchmark_threshold_met'] and read(OLD/'metrics.json')['candidate_adopted'] is False
    for root,count in ((AOC4,14),(AOC,4)):
        unit=read(root/'unittest.exit.json');assert unit['accepted']
        if root==AOC4:assert {p.name for p in root.iterdir()}=={Path(p).name for p in unit['artifact_pins']}|{'unittest.exit.json'}
        assert read(root/'unittest_report.json')==dict(accepted=True,tests_run=count,failures=0,errors=0,skipped=0)
        assert len(read(root/'unittest_admission.json')['nodes'])==count
        for path,value in unit['artifact_pins'].items():assert pin(Path(path).read_bytes())==value,path
        for path,value in read(root/'registration.json')['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    cp=read(AOC/'checkpoint.json');assert cp['accepted'] and cp['prior_not_accepted_count']==25
    assert {p.name for p in AOC.iterdir()}==set(cp['root_map_before_checkpoint'])|{'checkpoint.json'}
    for name,value in cp['root_map_before_checkpoint'].items():assert pin((AOC/name).read_bytes())==value,name
    assert pin(BASE_HELPER.read_bytes())==reg['helper_pins'][str(BASE_HELPER)]
    assert len(HISTORY)==6
    for (path,expected_sha),expected_count in zip(HISTORY,(26,26,26,27,27,28)):
        assert sha256(path.read_bytes()).hexdigest()==expected_sha
        record=read(path);assert record['accepted'] and record['prior_not_accepted_count']==expected_count
        if path.name=='checkpoint.json':
            assert {p.name for p in path.parent.iterdir()}==set(record['root_map_before_checkpoint'])|{path.name}
            for name,value in record['root_map_before_checkpoint'].items():assert pin((path.parent/name).read_bytes())==value,name
        else:
            assert {p.name for p in path.parent.iterdir()}=={'origin_probe.py','inspection.json'}
            for source,value in record['input_pins'].items():assert pin(Path(source).read_bytes())==value,source
    latest=read(HISTORY[-1][0]);assert latest['all_cumulative_total_seconds']==705.9498328000147
    for path,value in read(HISTORY[-1][0].parent/'registration.json')['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    return reg,latest
def reuse_evidence():
    paths=[OLD/name for name in ('checkpoint.exit.json','registration.json','helper_snapshots.json','unittest.exit.json','unittest_admission.json','unittest_report.json','metrics.json')]
    for root in (AOC4,AOC):paths.extend(root/name for name in ('registration.json','helper_snapshots.json','unittest.exit.json','unittest_admission.json','unittest_report.json'))
    paths.extend((AOC/'checkpoint.json',AOC/'probe_import_discovery.receipt.json'))
    assert len(paths)==19
    return pins(paths)
def migration():
    result={}
    for old,current,count in ((ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v22.py',CORE,2),(ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v19.py',PROBE,1)):
        raw=old.read_bytes();assert raw.count(b'aoc_v8_non_authoritative')==count
        assert current.read_bytes()==raw.replace(b'aoc_v8_non_authoritative',b'aoc_v9_non_authoritative')
        result[str(current)]=dict(old_pin=pin(raw),new_pin=pin(current.read_bytes()),occurrences=count,raw_transform_equal=True)
    a=ast.parse(BASE_HELPER.read_bytes());b=ast.parse(HELPER.read_bytes())
    allowed={'_census_emit','_census_observer','_census_open_begin','_census_open_end','diagnostic_import_once'};changed=[]
    for before,after in zip(a.body,b.body):
        if type(before) is ast.FunctionDef and before.name in allowed:
            assert type(after) is ast.FunctionDef and after.name==before.name and ast.dump(before)!=ast.dump(after)
            changed.append(before.name);before.body=after.body=[ast.Pass()]
    assert set(changed)==allowed and ast.dump(a)==ast.dump(b)
    result['helper']=dict(base_pin=pin(BASE_HELPER.read_bytes()),new_pin=pin(HELPER.read_bytes()),only_five_census_bodies_changed=True)
    return result
def runtime_leaves():
    import zlib,io,tokenize,ctypes.wintypes,secrets,subprocess,encodings.utf_16_le,copy,dis,unittest,dataclasses,traceback,linecache
    runtime=Path(EXE).parent;origins={};paths=set()
    for name,module in sorted(tuple(sys.modules.items())):
        origin=getattr(getattr(module,'__spec__',None),'origin',None)
        if type(origin) is str and origin in ('built-in','frozen'):origins[name]=dict(kind=origin);continue
        if type(origin) is not str:continue
        path=Path(origin).absolute()
        if not path.is_relative_to(runtime):continue
        assert path.is_file();paths.add(path);cache=getattr(module,'__cached__',None)
        cached=Path(cache).absolute() if type(cache) is str and Path(cache).is_file() else None
        if cached is not None:assert cached.is_relative_to(runtime);paths.add(cached)
        origins[name]=dict(kind='conditional_disk_leaf',origin=str(path),pin=pin(path.read_bytes()),cached=None if cached is None else dict(path=str(cached),pin=pin(cached.read_bytes())))
    return origins,paths
def audit_matrix(parent, row):
    assert row['accepted'] and row['child_exit'] == 1
    r = row['result']
    child = r['child_record']
    assert child is not None
    frames = r['diagnostic']['census_frames']
    assert [f['passed'] for f in frames] == [0, 1, 32, 64, 96, 128, 160, 192, 224, 256]
    final = frames[-1]
    assert r['prefix_complete'] and r['census_terminal_reason'] == final['reason'] == 'prefix_complete'
    assert final['entered'] == final['passed'] == final['observed'] == 256 and final['rejected'] == final['diagnostic_error_count'] == 0
    assert final['active'] is False and final['inflight'] is False and (final['last_incomplete'] is None)
    baseline = read(AOC / 'probe_import_discovery.receipt.json')['result']['child_record']
    assert baseline['primary']['type'] == 'AuditCensusStop' and baseline['primary']['message'] == 'diagnostic_prefix_complete_64'
    def successor(value):
        if type(value) is str:return 'diagnostic_prefix_complete_256' if value=='diagnostic_prefix_complete_64' else value
        if type(value) is list:return [successor(v) for v in value]
        if type(value) is dict:return {k:successor(v) for k,v in value.items()}
        return value
    assert child['primary']==successor(baseline['primary']) and child['secondary']==successor(baseline['secondary'])
    assert parent.validate_prefix_observation(child,base64.b64decode(row['stderr_raw_base64']))==r['diagnostic']
    parent.validate_memory_observation(row['memory_observation']);assert row['drain_reason'] is None
    assert child['status'] == 'failed' and child['runtime_phase'] == 'UNRESOLVED' and (child['boundary_phase'] == 'FAULTED') and (child['resource_phase'] == 'CLOSED')
    assert child['runtime_was_live'] is False and child['import_profile'] is None and (r['adapter_import_return_observed'] is False)
    assert r['self_close_witness_present'] and child['self_handles_closed'] and (child['close_calls'] == [1, 1]) and child['dll_directory_close_returned']
    assert not child['guard']['faults'] and (not child['early_audit_blocked']) and (child['boundary_report']['violations'] == 0)
    drain = row['bounded_drain']
    assert not drain['killed'] and drain['pipes_closed'] and drain['reader_threads_terminal'] and (not drain['reader_errors']) and (not drain['cleanup'])
    assert not drain['stdout_truncated'] and (not drain['stderr_truncated'])
    assert row['parent_process_handle_closed'] and row['writer_thread_terminal'] and row['stdin_closed'] and (not row['writer_errors']) and (not row['cleanup'])
    assert len(base64.b64decode(row['stdout_raw_base64'])) <= 131072 and len(base64.b64decode(row['stderr_raw_base64'])) <= 32768
    for key in ('actual_F', 'run_authority', 'formal_result', 'resource_admission', 'production_seal', 'full_runtime_binding_verified', 'native_behavior_verified', 'permit_issued'):
        assert child[key] is False and row[key] is False
    return dict(accepted=True, policy_classified_selected_prefix_only=True, all_unselected_events_verified=False, candidate_adopted=False, guard_faults=0)
def check(reg):
    previous()
    for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
def spent(extra=0,kind='static'):
    result=dict(static=read(OUT/'registration.json')['registration_charged_seconds']+read(OUT/'size_admission.json')['charged_seconds'],unittest=0.0)
    for p in OUT.glob('*.exit.json'):
        row=read(p);result[row['kind']]+=row['charged_seconds']
    result[kind]+=extra;return result
def prereq(action,reg,after=False):
    required=PHASES[:PHASES.index(action)];assert {p.name for p in OUT.glob('*.exit.json')}=={name+'.exit.json' for name in required}
    expected=set(BASE_FILES)
    if action!='unittest':expected.add('pre_seal_findings.json')
    for name in required:expected.update(OUTPUTS[name]|{name+'.exit.json'})
    if after:expected.update(OUTPUTS[action])
    assert {p.name for p in OUT.iterdir()}==expected
    for name in required:
        row=read(OUT/(name+'.exit.json'));assert row['accepted'] and row['registration_pin']==pin((OUT/'registration.json').read_bytes())
        for path,value in row['artifact_pins'].items():assert pin(Path(path).read_bytes())==value,path
def register():
    started=time.perf_counter();assert {p.name for p in OUT.iterdir()}=={'driver.py','import_policy.json','size_admission.json'}
    old,prior=previous();parent=load(PARENT);assert parent.source()==old['source_pins']
    space_for({name:FILE_CAPS.get(name,16384) for name in ('helper_snapshots.json','transport.snapshot','command_size.json','registration.json')})
    size=read(OUT/'size_admission.json');assert size['accepted'] and size['command_utf16_units']<=30000 and size['migration']==migration()
    assert size['startup_profile_cap']==FILE_CAPS['startup_profile.json']==131072
    for path,value in size['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    helpers=[CORE,HELPER,PROBE,PARENT,GRAPH,TEST,Path(__file__).absolute()]
    save(OUT/'helper_snapshots.json',{str(p):base64.b64encode(p.read_bytes()).decode() for p in helpers})
    code=parent.transport()
    import subprocess
    command=[EXE,'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(OUT/'probe_import_discovery.plan.json'),'0'*64]
    units=len(subprocess.list2cmdline(command).encode('utf-16-le'))//2
    write_raw(OUT/'transport.snapshot',code)
    save(OUT/'command_size.json',dict(command_utf16_units=units,transport_pin=pin(code),cap=30000,before_spawn=True,actual_F=False,run_authority=False))
    assert units<=30000 and pin(code)==size['transport_pin']
    paths={Path(p) for p in old['input_pins']}
    paths.update(p for p in OLD.iterdir())
    for history_path,_ in HISTORY:
        paths.update(history_path.parent.iterdir())
        paths.update(Path(p) for p in read(history_path).get('input_pins',{}))
    paths.update(Path(p) for p in size['input_pins'])
    paths.update(Path(p) for p in read(HISTORY[-1][0].parent/'registration.json')['input_pins'])
    paths.update(Path(p) for p in reuse_evidence())
    paths.update(helpers+[SCOPE,CHECKPOINT,OUT/'size_admission.json',OUT/'helper_snapshots.json',OUT/'transport.snapshot',OUT/'command_size.json',OUT/'import_policy.json'])
    origins,leaves=runtime_leaves();assert origins==size['conditional_runtime_origins'];paths.update(leaves)
    graph=load(GRAPH,'_full_import_graph').inspect_imports()
    paths.update(ROOT/row['path'] for row in graph['modules'].values())
    tree=ast.parse(TEST.read_bytes());cls=next(n for n in tree.body if type(n) is ast.ClassDef and n.name=='Prefix256Tests')
    nodes=sorted('prefix256_tests.Prefix256Tests.'+n.name for n in cls.body if type(n) is ast.FunctionDef and n.name.startswith('test_'));assert len(nodes)==6
    inputs=pins(sorted(paths))
    for row in graph['modules'].values():assert inputs[str(ROOT/row['path'])]==row['pin'],row['path']
    cost=time.perf_counter()-started;assert cost<=2
    save(OUT/'registration.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',input_pins=inputs,helper_pins=pins(helpers),
        transport_pin=pin(code),command_utf16_units=units,source_pins=old['source_pins'],source_epoch=old['source_epoch'],migration=size['migration'],
        registration_charged_seconds=cost,predecessor_charged_seconds=prior['all_cumulative_charged_seconds'],prior_not_accepted_count=28,
        unit_tests=0,unit_tests_planned=6,unit_nodes=nodes,static_import_graph=graph,prior_unit_tests_reused=dict(image_pin=9,census=14,terminal=4),reuse_evidence_pins=reuse_evidence(),history_evidence_pins=pins(path for path,_ in HISTORY),conditional_runtime_origins=origins,independent_tcb_authenticated=False,
        caps=dict(static=22,unittest=5,total=27,files=30,bytes=4*1024**2),all_unselected_events_verified=False,candidate_adopted=False,actual_F=False,run_authority=False))
    print(canonical(dict(accepted=True,charge=cost,units=units,new_unit_tests=6)).decode())
def unit_child():
    global _ACTIVE_EXIT
    _ACTIVE_EXIT='unittest.exit.json'
    import unittest
    reg=read(OUT/'registration.json');check(reg);module=load(TEST,'prefix256_tests');suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    def nodes(s):return [n for c in s for n in nodes(c)] if isinstance(s,unittest.TestSuite) else [s.id()]
    actual=sorted(nodes(suite));assert actual==reg['unit_nodes'];save(OUT/'unittest_admission.json',dict(nodes=actual,before_test_calls=True))
    result=unittest.TextTestRunner(verbosity=2).run(suite);check(reg)
    report=dict(accepted=result.wasSuccessful() and result.testsRun==6 and not result.skipped,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped))
    save(OUT/'unittest_report.json',report)
    if not report['accepted']:raise SystemExit(1)
def run(action):
    global _ACTIVE_EXIT
    _ACTIVE_EXIT=action+'.exit.json'
    started=time.perf_counter();target=OUT/(action+'.exit.json');assert not target.exists();reg=read(OUT/'registration.json');cap=CAPS[action];kind='unittest' if action=='unittest' else 'static'
    accepted=False;error=None;streams=None;case=None
    try:
        check(reg);prereq(action,reg);budget=spent(cap,kind);assert budget[kind]<=reg['caps'][kind] and sum(budget.values())<=27
        parent=load(PARENT);assert pin(parent.transport())==reg['transport_pin']
        if action=='unittest':
            capture=load(CAPTURE,'_full_unit_capture')
            rc,out,err,why,obs=capture.bounded([EXE,'-B','-s',str(Path(__file__).absolute()),'unit_child'],cap-(time.perf_counter()-started)-.7)
            streams=dict(returncode=rc,error=why,stdout_pin=pin(out),stderr_pin=pin(err),stdout_raw_base64=base64.b64encode(out).decode(),stderr_raw_base64=base64.b64encode(err).decode(),process_observation=obs)
            assert rc==0 and why is None and obs['handle_closed'] and not obs['cleanup']
            drain=obs['bounded_drain'];assert drain['pipes_closed'] and drain['reader_threads_terminal'] and not drain['reader_errors'] and not drain['cleanup'] and not drain['killed'] and not drain['stdout_truncated'] and not drain['stderr_truncated']
            assert read(OUT/'unittest_report.json')['accepted']
        elif action=='pre_seal':
            summary=read(OUT/'pre_seal_findings.json');assert summary['must_fix_open']==[] and summary['helper_pins']==reg['helper_pins'] and summary['official_review'] is False
            save(OUT/'pre_seal_admission.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',diagnostic_only=True,summary_pin=pin((OUT/'pre_seal_findings.json').read_bytes()),actual_F=False,run_authority=False))
        elif action in ('discovery','audit_prefix'):
            case_name='discovery' if action=='discovery' else 'import_discovery'
            assert len(parent.canonical(parent.manifest(case_name,parent.transport())))<=65536
            space_for({name:FILE_CAPS.get(name,65536) for name in OUTPUTS[action]})
            parent.save=parent_save
            case=parent.one_case('discovery' if action=='discovery' else 'import_discovery',cap-(time.perf_counter()-started));assert case['accepted']
            if action=='audit_prefix':audit_matrix(parent,case)
        elif action=='profile_admission':
            profile_bytes=(OUT/'startup_profile.json').stat().st_size;assert profile_bytes<=FILE_CAPS['startup_profile.json']
            profile=read(OUT/'startup_profile.json');assert profile['bootstrap_pin']==reg['transport_pin']
            for path,value in profile['disk_file_observations'].items():assert pin(Path(path).read_bytes())==value,path
            save(OUT/'profile_admission.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',profile_bytes=profile_bytes,profile_cap=FILE_CAPS['startup_profile.json'],profile_pin=pin((OUT/'startup_profile.json').read_bytes()),transport_pin=reg['transport_pin'],helper_pins=reg['helper_pins'],
                environment_pin=pin(canonical(parent.environment())),registration_pin=pin((OUT/'registration.json').read_bytes()),discovery_receipt_pin=pin((OUT/'probe_discovery.receipt.json').read_bytes()),actual_F=False,run_authority=False))
        else:
            row=read(OUT/'probe_import_discovery.receipt.json');validation=audit_matrix(parent,row)
            save(OUT/'saved_report.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',metadata_only=True,diagnostic_accepted=True,audit_validation=validation,
                stages=row['result']['diagnostic']['stages'],graph_frames=row['result']['diagnostic']['graph_frames'],census_frames=row['result']['diagnostic']['census_frames'],
                memory_observation=row['memory_observation'],drain_reason=row['drain_reason'],all_unselected_events_verified=False,candidate_adopted=False,actual_F=False,run_authority=False,formal_result=False,resource_admission=False))
        check(reg);prereq(action,reg,after=True);accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)[:160]
    charge=time.perf_counter()-started;usage=spent(charge,kind);accepted=accepted and charge<=cap and usage[kind]<=reg['caps'][kind] and sum(usage.values())<=27
    previous=reg['predecessor_charged_seconds'];cumulative={**previous,'static':previous['static']+usage['static'],'unittest':previous['unittest']+usage['unittest']}
    record=dict(accepted=accepted,label=action,kind=kind,charged_seconds=charge,cap_seconds=cap,scope_charged_seconds=usage,all_cumulative_charged_seconds=cumulative,
        all_cumulative_total_seconds=sum(cumulative.values()),prior_not_accepted_count=28+sum(not read(p)['accepted'] for p in OUT.glob('*.exit.json'))+(not accepted),unit_tests=None if not (OUT/'unittest_report.json').exists() else read(OUT/'unittest_report.json')['tests_run'],unit_tests_planned=6,all_unselected_events_verified=False,candidate_adopted=False,
        registration_pin=pin((OUT/'registration.json').read_bytes()),artifact_pins=pins(p for p in OUT.iterdir() if p.is_file()),error=error,streams=streams,case_accepted=None if case is None else case['accepted'],authority='DRAFT_NONAUTHORITATIVE',actual_F=False,run_authority=False,formal_result=False,resource_admission=False)
    raw=canonical(record);paths=[p for p in OUT.iterdir() if p.is_file()];assert len(paths)+1<=30 and sum(p.stat().st_size for p in paths)+len(raw)<=4*1024**2
    write_raw(target,raw)
    print(canonical(dict(accepted=accepted,label=action,charge=charge,error=error)).decode())
    if not accepted:raise SystemExit(1)
def size_admission():
    import io,tokenize,subprocess,zlib
    started=time.perf_counter();target=OUT/'size_admission.json';assert {p.name for p in OUT.iterdir()}=={'driver.py','import_policy.json'};space_for({'size_admission.json':262144});old,prior=previous();migrated=migration()
    paths=[CORE,HELPER,PROBE,PARENT,CHECKPOINT,GRAPH,TEST,CAPTURE,Path(__file__).absolute(),SCOPE,OUT/'import_policy.json']
    parent=load(PARENT);sources=parent.source();code=parent.transport();origins,leaves=runtime_leaves();paths+=sorted(leaves);inputs=pins(paths)
    plan=parent.manifest('discovery',code);assert plan['import_helper']==dict(path=str(HELPER),pin=pin(HELPER.read_bytes()))
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
        input_pins=inputs,migration=migrated,conditional_runtime_origins=origins,startup_profile_cap=FILE_CAPS['startup_profile.json'],independent_tcb_authenticated=False,unit_tests=0,unit_tests_planned=6,all_unselected_events_verified=False,candidate_adopted=False,prefix_before_pin=pin(before),prefix_after_pin=pin(prefix),dictionary_pin=pin(prefix),intended_payload_pin=pin(intended),decoded_payload_pin=pin(decoded),
        packed_pin=pin(packed),transport_pin=pin(code),command_utf16_units=units,payload_byte_equal=True,payload_position_ast_equal=True,payload_code_equal=True,
        prefix_tokens_equal=True,prefix_ast_equal=True,prefix_exact_code_unchanged_claimed=False,eof=decoder.eof,unused=False,unconsumed=False,
        unit_children_launched=0,cold_children_launched=0,actual_F=False,run_authority=False))
    print(canonical(dict(accepted=charge<=2 and units<=30000,charge=charge,units=units,prefix_before=len(before),prefix_after=len(prefix))).decode())
    if charge>2 or units>30000:raise SystemExit(1)

if __name__=='__main__':
    if sys.argv[1:]==['size_admission']:
        _ACTIVE_EXIT='size_failure.json'
        started=time.perf_counter()
        try:size_admission()
        except BaseException as error:
            if not (OUT/'size_admission.json').exists():save(OUT/'size_failure.json',dict(accepted=False,kind='static',charged_seconds=time.perf_counter()-started,error=repr(error),actual_F=False,run_authority=False))
            raise
    elif sys.argv[1:]==['register']:
        _ACTIVE_EXIT='registration_failure.json'
        started=time.perf_counter()
        try:register()
        except BaseException as error:save(OUT/'registration_failure.json',dict(accepted=False,kind='static',charged_seconds=time.perf_counter()-started,error=repr(error),actual_F=False,run_authority=False));raise
    elif sys.argv[1:]==['unit_child']:unit_child()
    elif len(sys.argv)==2 and sys.argv[1] in PHASES:run(sys.argv[1])
    else:raise SystemExit('fixed prefix256 diagnostic scope')
