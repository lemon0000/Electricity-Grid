"""One method-only pin-dedup oracle and finite cost comparison; create-only."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time

OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_aoc_v5_non_authoritative'
HELPER=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_image_pin_v1.py'
BASE=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_census_v4.py'
TEST=ROOT/'tests/test_staged_rts24_saved_fresh_image_pin_v1.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_image_pin_scope_v1.md'
OLD_CHECKPOINT=ROOT/'experiments/staged_rts24_saved_fresh_audit_census_checkpoint_v5.py'
CAPTURE=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/capture.py'
EXE='D:/Miniconda3/envs/compute/python.exe'
PHASES=('unittest','pre_seal','saved');CAPS=dict(unittest=5,pre_seal=1,saved=2,checkpoint=1)
STDLIB_ROOTS=('ast','base64','copy','ctypes','ctypes.wintypes','dataclasses','dis','hashlib','importlib.util','importlib.machinery','io','json','linecache','os','pathlib','statistics','subprocess','threading','time','traceback','types','unittest')

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def save(path,value):
    with path.open('xb') as stream:stream.write(canonical(value))
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def pins(paths):return {str(path):pin(path.read_bytes()) for path in paths}
def stdlib_evidence():
    for name in STDLIB_ROOTS:importlib.import_module(name)
    runtime=Path(EXE).parent;origins={};files=set()
    for name,module in sorted(tuple(sys.modules.items())):
        origin=getattr(getattr(module,'__spec__',None),'origin',None)
        if type(origin) is str and origin in ('built-in','frozen'):
            origins[name]=dict(kind=origin);continue
        if type(origin) is not str:continue
        path=Path(origin).absolute()
        if not path.is_relative_to(runtime):continue
        assert path.is_file(),(name,origin);files.add(path)
        cached=getattr(module,'__cached__',None);cache=None
        if type(cached) is str and Path(cached).is_file():
            cache=Path(cached).absolute();assert cache.is_relative_to(runtime);files.add(cache)
        origins[name]=dict(kind='conditional_disk_leaf',origin=str(path),pin=pin(path.read_bytes()),cached=None if cache is None else dict(path=str(cache),pin=pin(cache.read_bytes())))
    for name in STDLIB_ROOTS:assert name in origins,name
    return origins,files
def previous():
    reg=read(OLD/'registration.json');checkpoint=read(OLD/'checkpoint.json')
    assert checkpoint['accepted'] and checkpoint['prior_not_accepted_count']==25 and checkpoint['all_cumulative_total_seconds']==665.1157785000134
    assert {p.name for p in OLD.iterdir()}==set(checkpoint['root_map_before_checkpoint'])|{'checkpoint.json'}
    for name,value in checkpoint['root_map_before_checkpoint'].items():assert pin((OLD/name).read_bytes())==value,name
    assert pin(OLD_CHECKPOINT.read_bytes())==checkpoint['checkpoint_script_pin']==read(OLD/'pre_seal_findings.json')['checkpoint_script_pin']
    for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    for path,value in reg['source_pins'].items():assert pin((ROOT/path).read_bytes())==value,path
    return reg,checkpoint
def check(reg):
    previous()
    for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
def spent(extra=0,kind='static'):
    reg=read(OUT/'registration.json');usage=dict(static=reg['registration_charged_seconds'],unittest=0.0)
    for path in OUT.glob('*.exit.json'):
        row=read(path);usage[row['kind']]+=row['charged_seconds']
    usage[kind]+=extra;return usage
def register():
    started=time.perf_counter();assert {p.name for p in OUT.iterdir()}=={'driver.py'};old,prior=previous()
    assert sys.version==read(OLD/'import_policy.json')['python'] and Path(sys.executable).absolute()==Path(EXE)
    helpers=[HELPER,BASE,TEST,Path(__file__).absolute()]
    save(OUT/'helper_snapshots.json',{str(path):base64.b64encode(path.read_bytes()).decode() for path in helpers})
    cls=next(node for node in ast.parse(TEST.read_bytes()).body if type(node) is ast.ClassDef and node.name=='ImagePinTests')
    nodes=sorted('image_pin_tests.ImagePinTests.'+node.name for node in cls.body if type(node) is ast.FunctionDef and node.name.startswith('test_'))
    assert len(nodes)==9
    paths={Path(path) for path in old['input_pins']};paths.update(path for path in OLD.iterdir() if path.is_file())
    runtime=Path(EXE).parent
    paths.update(helpers+[SCOPE,OLD_CHECKPOINT,CAPTURE,OUT/'helper_snapshots.json',Path(EXE),runtime/'python312.dll',runtime/'Lib/statistics.py'])
    paths.update(runtime/'Lib/json'/name for name in ('__init__.py','encoder.py','decoder.py'))
    origins,stdlib_files=stdlib_evidence();paths.update(stdlib_files)
    inputs=pins(sorted(paths));charge=time.perf_counter()-started
    save(OUT/'registration.json',dict(accepted=charge<=2,authority='DRAFT_NONAUTHORITATIVE',kind='static',registration_charged_seconds=charge,cap_seconds=2,
        input_pins=inputs,helper_pins=pins(helpers),unit_nodes=nodes,conditional_stdlib_origins=origins,stdlib_roots=STDLIB_ROOTS,independent_tcb_authenticated=False,source_pins=old['source_pins'],source_epoch=old['source_epoch'],python=sys.version,
        predecessor_charged_seconds=prior['all_cumulative_charged_seconds'],prior_not_accepted_count=25,caps=dict(static=8,unittest=5,total=13,files=16,bytes=2*1024**2),
        cold_children_launched=0,adapter_imports=0,actual_F=False,run_authority=False))
    print(canonical(dict(accepted=charge<=2,charge=charge,nodes=len(nodes))).decode())
    if charge>2:raise SystemExit(1)
def unit_child():
    import unittest
    reg=read(OUT/'registration.json');check(reg);before,_=stdlib_evidence()
    assert before==reg['conditional_stdlib_origins']
    module=load(TEST,'image_pin_tests');suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    def nodes(suite):return [node for child in suite for node in nodes(child)] if isinstance(suite,unittest.TestSuite) else [suite.id()]
    actual=sorted(nodes(suite));assert actual==reg['unit_nodes'];save(OUT/'unittest_admission.json',dict(nodes=actual,before_test_calls=True))
    result=unittest.TextTestRunner(verbosity=2).run(suite);check(reg);after,_=stdlib_evidence()
    assert after==reg['conditional_stdlib_origins']
    report=dict(accepted=result.wasSuccessful() and result.testsRun==9 and not result.skipped,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped))
    save(OUT/'unittest_report.json',report)
    if not report['accepted']:raise SystemExit(1)
def prereq(action,reg):
    if action=='checkpoint':required=PHASES if (OUT/'saved.exit.json').exists() else ('unittest',)
    else:required=PHASES[:PHASES.index(action)]
    assert {path.name for path in OUT.glob('*.exit.json')}=={name+'.exit.json' for name in required}
    for name in required:
        row=read(OUT/(name+'.exit.json'));assert row['registration_pin']==pin((OUT/'registration.json').read_bytes())
        if action!='checkpoint' or required==PHASES:assert row['accepted']
        for path,value in row['artifact_pins'].items():assert pin(Path(path).read_bytes())==value,path
    if action=='checkpoint' and required!=PHASES:assert read(OUT/'unittest.exit.json')['accepted'] is False
def run(action):
    started=time.perf_counter();reg=read(OUT/'registration.json');assert reg['accepted']
    target=OUT/(action+'.exit.json');assert not target.exists();cap=CAPS[action];kind='unittest' if action=='unittest' else 'static'
    accepted=False;error=None;streams=None;observation=None
    try:
        check(reg);prereq(action,reg);usage=spent(cap,kind);assert usage[kind]<=reg['caps'][kind] and sum(usage.values())<=13
        if action=='unittest':
            capture=load(CAPTURE,'_image_pin_capture');rc,out,err,why,obs=capture.bounded([EXE,'-B','-s',str(Path(__file__).absolute()),'unit_child'],cap-(time.perf_counter()-started)-.7)
            streams=dict(returncode=rc,error=why,stdout_pin=pin(out),stderr_pin=pin(err),stdout_raw_base64=base64.b64encode(out).decode(),stderr_raw_base64=base64.b64encode(err).decode(),process_observation=obs)
            assert len(out)<=65536 and len(err)<=16384 and rc==0 and why is None and obs['handle_closed'] and not obs['cleanup']
            drain=obs['bounded_drain'];assert drain['pipes_closed'] and drain['reader_threads_terminal'] and not drain['reader_errors'] and not drain['cleanup'] and not drain['stdout_truncated'] and not drain['stderr_truncated']
            assert read(OUT/'unittest_report.json')['accepted']
        elif action=='pre_seal':
            findings=read(OUT/'pre_seal_findings.json');assert findings['must_fix_open']==[] and findings['helper_pins']==reg['helper_pins'] and findings['official_review'] is False
            save(OUT/'pre_seal_admission.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',findings_pin=pin((OUT/'pre_seal_findings.json').read_bytes()),actual_F=False,run_authority=False))
        else:
            unit=read(OUT/'unittest_report.json') if (OUT/'unittest_report.json').exists() else None
            metrics=read(OUT/'metrics.json') if (OUT/'metrics.json').exists() else None
            if metrics is not None:assert (OUT/'metrics.json').stat().st_size<=65536
            if action=='saved':assert unit is not None and unit['accepted'] and metrics is not None and metrics['benchmark_threshold_met']
            observation=dict(method_fixture_only=True,unit_report=unit,metrics_pin=None if metrics is None else pin((OUT/'metrics.json').read_bytes()),
                benchmark_threshold_met=None if metrics is None else metrics['benchmark_threshold_met'],candidate_adopted=False,cold_successor_validation_still_required=True,
                cold_children_launched=0,adapter_imports=0,actual_F=False,run_authority=False,formal_result=False,resource_admission=False)
            if action=='saved':save(OUT/'saved_snapshot.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',metadata_only=True,**observation))
        check(reg);prereq(action,reg);accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)[:180]
    charge=time.perf_counter()-started;usage=spent(charge,kind);accepted=accepted and charge<=cap and usage[kind]<=reg['caps'][kind] and sum(usage.values())<=13
    previous=reg['predecessor_charged_seconds'];cumulative={**previous,'static':previous['static']+usage['static'],'unittest':previous['unittest']+usage['unittest']}
    not_accepted=25+sum(not read(path)['accepted'] for path in OUT.glob('*.exit.json'))+(not accepted)
    row=dict(accepted=accepted,label=action,authority='DRAFT_NONAUTHORITATIVE',kind=kind,charged_seconds=charge,cap_seconds=cap,
        scope_charged_seconds=usage,all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),prior_not_accepted_count=not_accepted,
        registration_pin=pin((OUT/'registration.json').read_bytes()),artifact_pins=pins(path for path in OUT.iterdir() if path.is_file()),error=error,streams=streams,observation=observation,
        source_epoch=reg['source_epoch'],actual_F=False,run_authority=False,production_seal=False,formal_result=False,scientific_evidence_adopted=False,resource_admission=False)
    raw=canonical(row);files=[path for path in OUT.iterdir() if path.is_file()];assert len(files)+1<=16 and sum(path.stat().st_size for path in files)+len(raw)<=2*1024**2
    with target.open('xb') as stream:stream.write(raw)
    print(canonical(dict(accepted=accepted,label=action,charge=charge,error=error,total=sum(cumulative.values()),not_accepted=not_accepted)).decode())
    if not accepted:raise SystemExit(1)

if __name__=='__main__':
    if sys.argv[1:]==['register']:
        started=time.perf_counter()
        try:register()
        except BaseException as error:
            if not (OUT/'registration.json').exists():save(OUT/'registration_failure.json',dict(accepted=False,kind='static',charged_seconds=time.perf_counter()-started,error=repr(error),actual_F=False,run_authority=False))
            raise
    elif sys.argv[1:]==['unit_child']:unit_child()
    elif len(sys.argv)==2 and sys.argv[1] in (*PHASES,'checkpoint'):run(sys.argv[1])
    else:raise SystemExit('fixed method-only image-pin scope')
