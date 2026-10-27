"""Create-only method candidate: one unit child, zero cold/import children."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time

OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_pfc_v1_non_authoritative'
BASE=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_census512_parts_v1.py'
HELPER=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_image_none_v1.py'
TRANSFORM=ROOT/'experiments/staged_rts24_saved_fresh_image_none_transform_v1.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v25.py'
BASE_PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v24.py'
TEST=ROOT/'tests/test_staged_rts24_saved_fresh_image_none_v1.py'
FIXTURE=ROOT/'tests/test_staged_rts24_saved_fresh_image_pin_v1.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_image_none_scope_v1.md'
CAPTURE=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/capture.py'
EXE='D:/Miniconda3/envs/compute/python.exe'
PHASES=('unittest','pre_seal','saved');CAPS=dict(unittest=6,pre_seal=2,saved=2,checkpoint=2)
STDLIB_ROOTS=('encodings.utf_16_le','ast','base64','copy','ctypes','ctypes.wintypes','dataclasses','dis','hashlib','importlib.util','importlib.machinery','io','json','linecache','os','pathlib','statistics','subprocess','threading','time','traceback','types','unittest')
FALSE=dict(candidate_adopted=False,production_helper_selected=False,all_unselected_events_verified=False,
    actual_F=False,run_authority=False,production_seal=False,formal_result=False,scientific_evidence_adopted=False,resource_admission=False,
    native_behavior_verified=False,full_runtime_binding_verified=False,full_P1_content_verified=False,independent_root_verified=False,
    role_bootstrap=False,permit_issued=False,F_launch_admitted=False,native_authorized=False)


def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def pins(paths):return {str(p):pin(p.read_bytes()) for p in paths}
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def save(path,value):
    raw=canonical(value);limits={'registration.json':524288,'helper_snapshots.json':524288,'metrics.json':65536}
    assert path.parent==OUT and not path.exists() and len(raw)<=limits.get(path.name,131072)
    files=[p for p in OUT.iterdir() if p.is_file()];assert len(files)==len(list(OUT.iterdir()))
    reserve=0 if path.name=='checkpoint.exit.json' or (OUT/'checkpoint.exit.json').exists() else 131072
    assert len(files)+1+(reserve>0)<=20 and sum(p.stat().st_size for p in files)+len(raw)+reserve<=2*1024**2
    with path.open('xb') as stream:stream.write(raw)


def previous():
    raw=(OLD/'checkpoint.json').read_bytes()
    assert sha256(raw).hexdigest()=='1e22ac65fd23a40ea4f5e83c33081f6f7e5299ab9779339e78da48a4f6386f85'
    checkpoint=json.loads(raw);reg=read(OLD/'registration.json')
    assert checkpoint['accepted'] and checkpoint['prior_not_accepted_count']==30 and checkpoint['all_cumulative_total_seconds']==757.4680411000547
    assert {p.name for p in OLD.iterdir()}==set(checkpoint['root_map_before_checkpoint'])|{'checkpoint.json'}
    for name,value in checkpoint['root_map_before_checkpoint'].items():assert pin((OLD/name).read_bytes())==value,name
    for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    for path,value in reg['source_pins'].items():assert pin((ROOT/path).read_bytes())==value,path
    assert reg['source_epoch']=='acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'
    return reg,checkpoint


def stdlib_evidence():
    for name in STDLIB_ROOTS:importlib.import_module(name)
    runtime=Path(EXE).parent;origins={};files=set()
    for name,module in sorted(tuple(sys.modules.items())):
        origin=getattr(getattr(module,'__spec__',None),'origin',None)
        if type(origin) is str and origin in ('built-in','frozen'):origins[name]=dict(kind=origin);continue
        if type(origin) is not str:continue
        path=Path(origin).absolute()
        if not path.is_relative_to(runtime):continue
        assert path.is_file();files.add(path);cache=getattr(module,'__cached__',None)
        cached=Path(cache).absolute() if type(cache) is str and Path(cache).is_file() else None
        if cached is not None:assert cached.is_relative_to(runtime);files.add(cached)
        origins[name]=dict(kind='conditional_disk_leaf',origin=str(path),pin=pin(path.read_bytes()),cached=None if cached is None else dict(path=str(cached),pin=pin(cached.read_bytes())))
    for name in STDLIB_ROOTS:assert name in origins,name
    return origins,files


def check(reg):
    previous()
    for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path


def register():
    started=time.perf_counter();assert {p.name for p in OUT.iterdir()}=={'driver.py'}
    old,prior=previous();assert sys.version==old['python'] and Path(sys.executable).absolute()==Path(EXE)
    helpers=[HELPER,BASE,TRANSFORM,PROBE,BASE_PROBE,TEST,FIXTURE,Path(__file__).absolute()]
    transform=load(TRANSFORM,'_none_registration_transform')
    assert transform.helper(BASE.read_text(encoding='utf-8'))==HELPER.read_bytes()
    assert transform.probe(BASE_PROBE.read_text(encoding='utf-8'))==PROBE.read_bytes()
    for path in helpers:compile(path.read_bytes(),str(path),'exec',dont_inherit=True,optimize=0)
    names=set()
    for path,cls_name in ((FIXTURE,'ImagePinTests'),(TEST,'ImageNoneTests')):
        cls=next(n for n in ast.parse(path.read_bytes()).body if type(n) is ast.ClassDef and n.name==cls_name)
        names.update(n.name for n in cls.body if type(n) is ast.FunctionDef and n.name.startswith('test_'))
    nodes=sorted('image_none_tests.ImageNoneTests.'+name for name in names);assert len(nodes)==12
    save(OUT/'helper_snapshots.json',{str(path):base64.b64encode(path.read_bytes()).decode('ascii') for path in helpers})
    paths={Path(path) for path in old['input_pins']};paths.update(OLD.iterdir());paths.update(helpers+[SCOPE,CAPTURE,OUT/'helper_snapshots.json',Path(EXE),Path(EXE).parent/'python312.dll'])
    origins,leaves=stdlib_evidence();paths.update(leaves);inputs=pins(sorted(paths));charge=time.perf_counter()-started
    reg=dict(accepted=charge<=2,authority='DRAFT_NONAUTHORITATIVE',kind='static',registration_charged_seconds=charge,cap_seconds=2,
        input_pins=inputs,helper_pins=pins(helpers),unit_nodes=nodes,conditional_stdlib_origins=origins,independent_tcb_authenticated=False,
        source_pins=old['source_pins'],source_epoch=old['source_epoch'],python=sys.version,predecessor_charged_seconds=prior['all_cumulative_charged_seconds'],
        prior_not_accepted_count=30,caps=dict(static=8,unittest=6,total=14,files=20,bytes=2*1024**2),cold_children_launched=0,adapter_imports=0,**FALSE)
    save(OUT/'registration.json',reg)
    print(canonical(dict(accepted=reg['accepted'],charge=charge,nodes=len(nodes),inputs=len(inputs))).decode())
    if not reg['accepted']:raise SystemExit(1)


def unit_child():
    import unittest
    reg=read(OUT/'registration.json');check(reg);before,_=stdlib_evidence();assert before==reg['conditional_stdlib_origins']
    module=load(TEST,'image_none_tests');suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    def nodes(suite):return [n for child in suite for n in nodes(child)] if isinstance(suite,unittest.TestSuite) else [suite.id()]
    actual=sorted(nodes(suite));assert actual==reg['unit_nodes']
    save(OUT/'unittest_admission.json',dict(nodes=actual,before_test_calls=True))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert not module._GATE['active']
    check(reg);after,_=stdlib_evidence();assert after==reg['conditional_stdlib_origins']
    report=dict(accepted=result.wasSuccessful() and result.testsRun==12 and not result.skipped,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped))
    save(OUT/'unittest_report.json',report)
    if not report['accepted']:raise SystemExit(1)


def spent():
    reg=read(OUT/'registration.json');usage=dict(static=reg['registration_charged_seconds'],unittest=0.0)
    for path in OUT.glob('*.exit.json'):
        row=read(path);usage[row['kind']]+=row['charged_seconds']
    return usage


def prereq(action):
    required=tuple(n for n in PHASES if (OUT/(n+'.exit.json')).exists()) if action=='checkpoint' else PHASES[:PHASES.index(action)]
    assert required==PHASES[:len(required)]
    if action=='checkpoint':assert required and (required==PHASES or not read(OUT/(required[-1]+'.exit.json'))['accepted'])
    assert {p.name for p in OUT.glob('*.exit.json')}=={n+'.exit.json' for n in required}
    for index,name in enumerate(required):
        row=read(OUT/(name+'.exit.json'));assert row['registration_pin']==pin((OUT/'registration.json').read_bytes())
        if action!='checkpoint' or index<len(required)-1:assert row['accepted']
        for path,value in row['artifact_pins'].items():assert pin(Path(path).read_bytes())==value,path


def validate_metrics(m):
    metric_false=set(FALSE)|{'cross_call_cache'}
    keys={'authority','method_fixture_only','synthetic_dispatch_only','rounds','without_dispatch','total_ratio_new_over_old',
        'median_ratio_new_over_old','without_dispatch_ratio_new_over_old','dispatch_threshold','without_dispatch_threshold',
        'benchmark_threshold_met','hook_installed','hook_deactivated','hook_uninstalled','fixture_rows','cold_children_launched','adapter_imports'}|metric_false
    assert type(m) is dict and set(m)==keys and m['authority']=='DRAFT_NONAUTHORITATIVE'
    assert all(m[k] is False for k in metric_false|{'hook_uninstalled'})
    assert all(m[k] is True for k in ('method_fixture_only','synthetic_dispatch_only','hook_installed','hook_deactivated'))
    assert all(type(m[k]) is int and m[k]==0 for k in ('cold_children_launched','adapter_imports'))
    assert type(m['fixture_rows']) is dict and set(m['fixture_rows'])=={'global_bindings','own_bindings','attribute_bindings'}
    assert all(type(v) is int and v>0 for v in m['fixture_rows'].values())
    def positive(v):return type(v) is float and 0<v<float('inf')
    def observation(r,variant,scans,audited):
        assert type(r) is dict and set(r)=={'variant','scans','seconds','id_dispatch_calls','none_dispatch_calls'}
        assert r['variant']==variant and type(r['scans']) is int and r['scans']==scans and positive(r['seconds'])
        assert all(type(r[k]) is int and r[k]>=0 for k in ('id_dispatch_calls','none_dispatch_calls'))
        if audited:
            assert r['id_dispatch_calls']>r['none_dispatch_calls']>0 and r['id_dispatch_calls']%scans==r['none_dispatch_calls']%scans==0
        else:assert r['id_dispatch_calls']==r['none_dispatch_calls']==0
    assert type(m['rounds']) is list and len(m['rounds'])==3
    old=[];new=[];counts=[]
    for index,(round_,order) in enumerate(zip(m['rounds'],(('old','new'),('new','old'),('old','new'))),1):
        assert type(round_) is dict and set(round_)=={'round','order','observations'}
        assert type(round_['round']) is int and round_['round']==index and round_['order']==list(order)
        rows=round_['observations'];assert type(rows) is list and len(rows)==2
        for r,name in zip(rows,order):observation(r,name,48,True)
        a=next(r for r in rows if r['variant']=='old');b=next(r for r in rows if r['variant']=='new')
        assert b['none_dispatch_calls']==48 and a['none_dispatch_calls']>48
        assert a['id_dispatch_calls']-b['id_dispatch_calls']==a['none_dispatch_calls']-b['none_dispatch_calls']
        counts.append((a['id_dispatch_calls'],b['id_dispatch_calls'],a['none_dispatch_calls']))
        old.append(a['seconds']);new.append(b['seconds'])
    assert counts[0]==counts[1]==counts[2]
    plain=m['without_dispatch'];assert type(plain) is list and len(plain)==2
    for r,name in zip(plain,('old','new')):observation(r,name,20,False)
    ratios=(sum(new)/sum(old),sorted(new)[1]/sorted(old)[1],plain[1]['seconds']/plain[0]['seconds'])
    for key,value in zip(('total_ratio_new_over_old','median_ratio_new_over_old','without_dispatch_ratio_new_over_old'),ratios):
        assert positive(m[key]) and abs(m[key]-value)<=1e-12*max(1,abs(value))
    assert type(m['dispatch_threshold']) is float and m['dispatch_threshold']==.95
    assert type(m['without_dispatch_threshold']) is float and m['without_dispatch_threshold']==1.20
    met=ratios[0]<=.95 and ratios[1]<=.95 and ratios[2]<=1.20
    assert m['benchmark_threshold_met'] is met
    return met


def run(action):
    started=time.perf_counter();reg=read(OUT/'registration.json');assert reg['accepted']
    cap=CAPS[action];kind='unittest' if action=='unittest' else 'static';target=OUT/(action+'.exit.json');assert not target.exists()
    accepted=False;error=None;streams=None;observation=None
    try:
        check(reg);prereq(action);usage=spent();usage[kind]+=cap
        assert usage[kind]<=reg['caps'][kind] and sum(usage.values())<=14
        if action=='unittest':
            files=[p for p in OUT.iterdir() if p.is_file()]
            assert len(files)+5<=20 and sum(p.stat().st_size for p in files)+65536+2*16384+2*131072<=2*1024**2
            capture=load(CAPTURE,'_none_unit_capture')
            rc,out,err,why,obs=capture.bounded([EXE,'-B','-s',str(Path(__file__).absolute()),'unit_child'],cap-(time.perf_counter()-started)-.7)
            streams=dict(returncode=rc,error=why,stdout_pin=pin(out),stderr_pin=pin(err),stdout_raw_base64=base64.b64encode(out).decode(),stderr_raw_base64=base64.b64encode(err).decode(),process_observation=obs)
            assert len(out)<=65536 and len(err)<=16384 and rc==0 and why is None and obs['handle_closed'] and not obs['cleanup']
            drain=obs['bounded_drain'];assert drain['pipes_closed'] and drain['reader_threads_terminal'] and not drain['reader_errors'] and not drain['cleanup'] and not drain['stdout_truncated'] and not drain['stderr_truncated']
            assert read(OUT/'unittest_report.json')['accepted']
        elif action=='pre_seal':
            findings=read(OUT/'pre_seal_findings.json');assert findings['must_fix_open']==[] and findings['helper_pins']==reg['helper_pins'] and findings['official_review'] is False
            save(OUT/'pre_seal_admission.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',findings_pin=pin((OUT/'pre_seal_findings.json').read_bytes()),**FALSE))
        else:
            unit=read(OUT/'unittest_report.json') if (OUT/'unittest_report.json').exists() else None
            metrics=read(OUT/'metrics.json') if (OUT/'metrics.json').exists() else None
            if metrics is not None:
                assert (OUT/'metrics.json').stat().st_size<=65536
                benefit=validate_metrics(metrics)
            if action=='saved':assert unit is not None and unit['accepted'] and metrics is not None and benefit
            observation=dict(method_fixture_only=True,synthetic_dispatch_only=True,unit_report=unit,metrics_pin=None if metrics is None else pin((OUT/'metrics.json').read_bytes()),
                benchmark_threshold_met=None if metrics is None else metrics['benchmark_threshold_met'],cold_successor_validation_still_required=True,cold_children_launched=0,adapter_imports=0,**FALSE)
            if action=='saved':save(OUT/'saved_snapshot.json',dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',metadata_only=True,**observation))
        check(reg);prereq(action);accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)[:180]
    charge=time.perf_counter()-started;usage=spent();usage[kind]+=charge
    accepted=accepted and charge<=cap and usage[kind]<=reg['caps'][kind] and sum(usage.values())<=14
    previous_usage=reg['predecessor_charged_seconds'];cumulative={**previous_usage,'static':previous_usage['static']+usage['static'],'unittest':previous_usage['unittest']+usage['unittest']}
    not_accepted=30+sum(not read(p)['accepted'] for p in OUT.glob('*.exit.json'))+(not accepted)
    row=dict(accepted=accepted,label=action,authority='DRAFT_NONAUTHORITATIVE',kind=kind,charged_seconds=charge,cap_seconds=cap,scope_charged_seconds=usage,
        all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),prior_not_accepted_count=not_accepted,
        registration_pin=pin((OUT/'registration.json').read_bytes()),artifact_pins=pins(p for p in OUT.iterdir() if p.is_file()),error=error,streams=streams,observation=observation,
        diagnostic_accepted=accepted and action=='checkpoint' and (OUT/'saved.exit.json').exists() and read(OUT/'saved.exit.json')['accepted'],
        source_epoch=reg['source_epoch'],cold_children_launched=0,adapter_imports=0,**FALSE)
    save(target,row)
    print(canonical(dict(accepted=accepted,label=action,charge=charge,error=error,total=sum(cumulative.values()),not_accepted=not_accepted)).decode())
    if not accepted:raise SystemExit(1)


def registration_checkpoint():
    started=time.perf_counter();old,prior=previous()
    records=[p for p in OUT.iterdir() if p.name in ('registration.json','registration_failure.json')]
    assert len(records)==1 and not read(records[0])['accepted'];record=read(records[0]);charge=time.perf_counter()-started
    usage=dict(static=record.get('charged_seconds',record.get('registration_charged_seconds',0))+charge,unittest=0.0)
    previous_usage=prior['all_cumulative_charged_seconds'];cumulative={**previous_usage,'static':previous_usage['static']+usage['static']};accepted=charge<=2 and usage['static']<=8
    save(OUT/'checkpoint.exit.json',dict(accepted=accepted,authority='DRAFT_NONAUTHORITATIVE',acceptance_scope='rejection_metadata_only',diagnostic_accepted=False,kind='static',charged_seconds=charge,cap_seconds=2,
        scope_charged_seconds=usage,all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),prior_not_accepted_count=31+(not accepted),
        artifact_pins=pins(p for p in OUT.iterdir() if p.is_file()),executed_input_bytes_verified='input_pins' in record,source_epoch=old['source_epoch'],cold_children_launched=0,adapter_imports=0,**FALSE))
    print(canonical(dict(accepted=accepted,diagnostic_accepted=False,total=sum(cumulative.values()),not_accepted=31+(not accepted))).decode())
    if not accepted:raise SystemExit(1)


if __name__=='__main__':
    if sys.argv[1:]==['register']:
        started=time.perf_counter()
        try:register()
        except BaseException as error:
            if not (OUT/'registration.json').exists():save(OUT/'registration_failure.json',dict(accepted=False,kind='static',charged_seconds=time.perf_counter()-started,error=repr(error),**FALSE))
            raise
    elif sys.argv[1:]==['unit_child']:unit_child()
    elif sys.argv[1:]==['checkpoint'] and (not (OUT/'registration.json').exists() or not read(OUT/'registration.json')['accepted']):registration_checkpoint()
    elif len(sys.argv)==2 and sys.argv[1] in (*PHASES,'checkpoint'):run(sys.argv[1])
    else:raise SystemExit('fixed method-only None-id scope')
