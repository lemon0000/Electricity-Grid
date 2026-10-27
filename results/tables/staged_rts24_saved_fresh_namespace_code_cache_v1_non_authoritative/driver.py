"""One bounded logical unit group plus metadata-only saved verification."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time

OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
HELPER=ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_v3.py'
ORACLE=ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_v2.py'
TEST=ROOT/'tests/test_staged_rts24_saved_fresh_namespace_code_cache_v1.py'
BASE=ROOT/'tests/test_staged_rts24_saved_fresh_entry_namespace_v2.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v3.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_namespace_code_cache_scope_v1.md'
PRIOR=ROOT/'results/tables/staged_rts24_saved_fresh_runtime_guard_checkpoint_v1_non_authoritative/snapshot.json'
CAPTURE=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/capture.py'
EXE='D:/Miniconda3/envs/compute/python.exe'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(p):return json.loads(p.read_bytes())
def save(p,v):
    with p.open('xb') as f:f.write(canonical(v))
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def pins(paths):return {str(p):pin(p.read_bytes()) for p in paths}
def predecessor():
    prior=read(PRIOR);assert prior['accepted'] and prior['prior_not_accepted_count']==20
    for name,rows in prior['root_maps'].items():
        root=ROOT/('results/tables/staged_rts24_saved_fresh_'+name+'_v1_non_authoritative')
        assert {p.name:pin(p.read_bytes()) for p in root.iterdir() if p.is_file()}==rows,name
    reg=read(ROOT/'results/tables/staged_rts24_saved_fresh_runtime_guard_v1_non_authoritative/registration.json')
    for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    return prior,reg
def check(reg):
    predecessor()
    for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
def cost(extra=0,kind='static'):
    result=dict(static=read(OUT/'registration.json')['registration_charged_seconds'],unittest=0.0)
    for p in OUT.glob('*.exit.json'):
        row=read(p);result[row['kind']]+=row['charged_seconds']
    result[kind]+=extra;return result
def register():
    started=time.perf_counter();assert not (OUT/'registration.json').exists();prior,old=predecessor()
    helpers=[HELPER,ORACLE,TEST,BASE,PROBE,Path(__file__).absolute()]
    save(OUT/'helper_snapshots.json',{str(p):base64.b64encode(p.read_bytes()).decode() for p in helpers})
    def tests(path,cls):
        node=next(n for n in ast.parse(path.read_bytes()).body if type(n) is ast.ClassDef and n.name==cls)
        return [n.name for n in node.body if type(n) is ast.FunctionDef and n.name.startswith('test_')]
    nodes=sorted(['namespace_cache_tests.NamespaceCacheRegression.'+n for n in tests(BASE,'EntryNamespaceTests')]+['namespace_cache_tests.CodeCacheEquivalence.'+n for n in tests(TEST,'CodeCacheEquivalence')])
    files={Path(p) for p in old['input_pins']};files.update(helpers+[SCOPE,PRIOR,CAPTURE,OUT/'helper_snapshots.json'])
    for name in prior['root_maps']:files.update(p for p in (ROOT/('results/tables/staged_rts24_saved_fresh_'+name+'_v1_non_authoritative')).iterdir() if p.is_file())
    inputs=pins(sorted(files));charge=time.perf_counter()-started;assert charge<=2
    save(OUT/'registration.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',input_pins=inputs,helper_pins=pins(helpers),unit_nodes=nodes,
        source_epoch=prior['source_epoch'],source_pins=old['source_pins'],predecessor_charged_seconds=prior['all_cumulative_charged_seconds'],prior_not_accepted_count=20,
        registration_charged_seconds=charge,caps=dict(static=8,unittest=12,total=20,files=12,bytes=2*1024**2),actual_F=False,run_authority=False))
    print(canonical(dict(accepted=True,charge=charge,unit_nodes=len(nodes))).decode())
def unit_child():
    import unittest
    reg=read(OUT/'registration.json');check(reg);module=load(TEST,'namespace_cache_tests');suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    def nodes(suite):return [n for c in suite for n in nodes(c)] if isinstance(suite,unittest.TestSuite) else [suite.id()]
    actual=sorted(nodes(suite));assert actual==reg['unit_nodes'];save(OUT/'unittest_admission.json',dict(nodes=actual,before_test_calls=True,helper_pins=reg['helper_pins']))
    result=unittest.TextTestRunner(verbosity=1).run(suite);check(reg)
    save(OUT/'metrics.json',dict(authority='DRAFT_NONAUTHORITATIVE',cases=module.METRICS,whole_chain_speedup_verified=False,actual_F=False,run_authority=False))
    report=dict(accepted=result.wasSuccessful() and result.testsRun==len(actual) and not result.skipped,tests_run=result.testsRun,nodes=actual,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped))
    save(OUT/'unittest_report.json',report)
    if not report['accepted']:raise SystemExit(1)
def run(action):
    started=time.perf_counter();target=OUT/(action+'.exit.json');assert not target.exists();reg=read(OUT/'registration.json')
    cap=12 if action=='unittest' else 3;kind='unittest' if action=='unittest' else 'static';accepted=False;error=None;streams=None
    try:
        check(reg);budget=cost(cap,kind);assert budget[kind]<=reg['caps'][kind] and sum(budget.values())<=20
        if action=='unittest':
            assert not list(OUT.glob('*.exit.json'));capture=load(CAPTURE,'_cache_capture')
            rc,out,err,why,obs=capture.bounded([EXE,'-B','-s',str(Path(__file__).absolute()),'unit_child'],cap-(time.perf_counter()-started)-.7)
            streams=dict(returncode=rc,error=why,stdout_pin=pin(out),stderr_pin=pin(err),stdout_raw_base64=base64.b64encode(out).decode(),stderr_raw_base64=base64.b64encode(err).decode(),process_observation=obs)
            assert rc==0 and why is None and obs['handle_closed'] and not obs['cleanup']
            drain=obs['bounded_drain'];assert drain['pipes_closed'] and drain['reader_threads_terminal'] and not drain['reader_errors'] and not drain['cleanup'] and not drain['stdout_truncated'] and not drain['stderr_truncated']
            assert read(OUT/'unittest_report.json')['accepted']
        else:
            assert read(OUT/'unittest.exit.json')['accepted']
            for path,value in read(OUT/'unittest.exit.json')['artifact_pins'].items():assert pin(Path(path).read_bytes())==value,path
            for path,encoded in read(OUT/'helper_snapshots.json').items():assert Path(path).read_bytes()==base64.b64decode(encoded,validate=True)
            metrics=read(OUT/'metrics.json');assert {v['case'] for v in metrics['cases']}=={'shared_dag','actual_entry'}
            actual=next(v for v in metrics['cases'] if v['case']=='actual_entry');assert actual['new_hash_calls']<actual['old_hash_calls']
            save(OUT/'saved_report.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',metadata_only=True,metrics_pin=pin((OUT/'metrics.json').read_bytes()),
                prior_not_accepted_count=20,actual_F=False,run_authority=False,formal_result=False,resource_admission=False))
        check(reg);accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)[:160]
    charge=time.perf_counter()-started;usage=cost(charge,kind);accepted=accepted and charge<=cap and usage[kind]<=reg['caps'][kind] and sum(usage.values())<=20
    previous=reg['predecessor_charged_seconds'];cumulative={**previous,'static':previous['static']+usage['static'],'unittest':previous['unittest']+usage['unittest']}
    record=dict(accepted=accepted,label=action,kind=kind,charged_seconds=charge,cap_seconds=cap,scope_charged_seconds=usage,
        all_cumulative_charged_seconds=cumulative,error=error,streams=streams,artifact_pins=pins(p for p in OUT.iterdir() if p.is_file()),
        registration_pin=pin((OUT/'registration.json').read_bytes()),authority='DRAFT_NONAUTHORITATIVE',actual_F=False,run_authority=False,formal_result=False,resource_admission=False)
    raw=canonical(record);files=[p for p in OUT.iterdir() if p.is_file()];assert len(files)+1<=12 and sum(p.stat().st_size for p in files)+len(raw)<=2*1024**2
    with target.open('xb') as f:f.write(raw)
    print(canonical(dict(accepted=accepted,label=action,charge=charge,error=error)).decode())
    if not accepted:raise SystemExit(1)
if __name__=='__main__':
    if sys.argv[1:]==['register']:
        started=time.perf_counter()
        try:register()
        except BaseException as error:
            save(OUT/'registration_failure.json',dict(accepted=False,kind='static',charged_seconds=time.perf_counter()-started,error=repr(error),actual_F=False,run_authority=False));raise
    elif sys.argv[1:]==['unit_child']:unit_child()
    elif len(sys.argv)==2 and sys.argv[1] in ('unittest','saved'):run(sys.argv[1])
    else:raise SystemExit('fixed cache-equivalence scope only')
