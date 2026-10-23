"""Runtime pins and controller faults; no full saved replay or native work."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from src import staged_rts24_shadow_runtime_v2 as runtime


def test_attempt_sources_bind_the_v2_contract():
    from experiments import staged_rts24_shadow_replay_v2 as driver
    assert driver.CONTRACT=='docs/plan/staged_deliverability_c_shadow_replay_contract_v2.md'
    assert driver.sources()[driver.CONTRACT]==driver.stamp(driver.ROOT/driver.CONTRACT)


def test_runtime_source_code_schema_and_bookend_are_stable():
    before,refs=runtime.snapshot()
    assert runtime.unchanged(before,refs)==before
    assert len(before['classes'])==20 and 'json' in before['stdlib']
    assert all('code_sha' in row for row in before['functions'].values())
    assert len(before['application_modules'])==38
    assert 'successor_monitor/_returned' in before['functions'] and 'monitor/_cleanup' in before['functions']


@pytest.mark.parametrize('fault',['candidate_path','new_parent','base_parent','name','fields','unchanged','snapshot_code',
    'module_set','extra','monitor_sys','candidate_sha','runtime_path','runtime_require','runtime_core'])
def test_successor_identity_drift_is_refused(monkeypatch,fault):
    if fault=='candidate_path':monkeypatch.setattr(runtime.candidate,'__file__',str(runtime.ROOT.parent/'elsewhere.py'))
    elif fault=='new_parent':monkeypatch.setattr(sys.modules['src'],'staged_rts24_plain_v2',object())
    elif fault=='base_parent':monkeypatch.setattr(runtime.shadow,'base',object())
    elif fault=='name':monkeypatch.setattr(runtime.shadow.ShadowMonitor,'NAME','different-monitor')
    elif fault=='fields':monkeypatch.setattr(runtime.candidate,'_KNOWN_FIELDS',())
    elif fault=='unchanged':monkeypatch.setattr(runtime,'unchanged',lambda before,refs:before)
    elif fault=='module_set':monkeypatch.setattr(runtime,'APP_NAMES',runtime.APP_NAMES[:-1])
    elif fault=='extra':monkeypatch.setattr(runtime,'EXTRA',runtime.EXTRA[:-1])
    elif fault=='monitor_sys':monkeypatch.setattr(runtime.shadow,'sys',object())
    elif fault=='candidate_sha':monkeypatch.setattr(runtime.candidate,'sha256',lambda b:b)
    elif fault=='runtime_path':monkeypatch.setattr(runtime,'Path',lambda p:p)
    elif fault=='runtime_require':monkeypatch.setattr(runtime,'require',lambda *a:None)
    elif fault=='runtime_core':monkeypatch.setattr(runtime,'core',object())
    else:
        code=runtime.snapshot.__code__
        monkeypatch.setattr(runtime.snapshot,'__code__',code.replace(co_consts=tuple('changed_domain' if v=='successor_domain' else v for v in code.co_consts)))
    with pytest.raises(ValueError):runtime.snapshot()


def test_runtime_value_code_pins_are_portable_between_fresh_controlled_processes():
    code='from src.staged_rts24_shadow_runtime_v2 import snapshot; import json; print(json.dumps(snapshot()[0],sort_keys=True))'
    values=[]
    for _ in range(2):
        result=subprocess.run([sys.executable,'-B','-s','-c',code],cwd=runtime.ROOT,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15,check=True)
        assert result.stderr==b'';values.append(json.loads(result.stdout))
    assert values[0]==values[1]
    assert values[0]['flags']==dict(no_user_site=1,dont_write_bytecode=True)


def test_normal_job_quiet_preserves_parent_loaded_runtime(tmp_path):
    from src.staged_rts24_process_guard_v1 import supervise
    before,refs=runtime.snapshot()
    record=supervise([sys.executable,'-B','-s','-c','import time; time.sleep(.25)'],cwd=runtime.ROOT,output=tmp_path,
        progress=tmp_path/'events.jsonl',limits=dict(wall_seconds=5,no_progress_seconds=5,
            rss_bytes=512*1024**2,output_bytes=1024**2,files=8))
    assert record['exit_code']==0 and record['stop_reason'] is None and record['job_quiet_confirmed'],record
    assert runtime.unchanged(before,refs)==before


def test_synthetic_stdlib_namespace_owner_change_is_refused(monkeypatch):
    import pyexpat
    monkeypatch.setattr(pyexpat,'errors',object())
    with pytest.raises(ValueError,match='synthetic stdlib owner differs'):runtime.snapshot()


@pytest.mark.parametrize('fault',['journal_path','monitor_path','package_path','parent_binding','sys_modules'])
def test_application_module_shadows_are_refused(monkeypatch,fault):
    if fault in ('journal_path','monitor_path'):
        module=runtime.journal if fault=='journal_path' else runtime.shadow
        monkeypatch.setattr(module,'__file__',str(runtime.ROOT.parent/Path(module.__file__).name))
    elif fault=='package_path':monkeypatch.setattr(sys.modules['src'],'__path__',[str(runtime.ROOT.parent/'src')])
    elif fault=='parent_binding':monkeypatch.setattr(sys.modules['src'],'staged_rts24_journal_v2',object())
    else:monkeypatch.setitem(sys.modules,runtime.journal.__name__,SimpleNamespace(__name__=runtime.journal.__name__))
    with pytest.raises(ValueError,match='application'):runtime.snapshot()


@pytest.mark.parametrize('fault',['code','module_path','json_options','class_descriptor','fallback'])
def test_runtime_drift_is_refused_without_observing_unknown_field(monkeypatch,fault):
    touches=[]
    if fault=='code':
        code=runtime.core.digest.__code__
        monkeypatch.setattr(runtime.core.digest,'__code__',code.replace(co_consts=tuple('ascii' if v=='utf-8' else v for v in code.co_consts)))
    elif fault=='module_path':monkeypatch.setattr(runtime.base.json,'__file__',str(runtime.ROOT/'wrong_json.py'))
    elif fault=='json_options':
        changed=dict(runtime.base.json.dumps.__kwdefaults__);changed['ensure_ascii']=1
        monkeypatch.setattr(runtime.base.json.dumps,'__kwdefaults__',changed)
    elif fault=='fallback':monkeypatch.setattr(runtime.candidate,'_legacy_plain',lambda v:v)
    else:
        cls,names=runtime.candidate._KNOWN_FIELDS[0]
        def getter(self):touches.append('field');raise RuntimeError('must not inspect value')
        monkeypatch.setattr(cls,names[0],property(getter),raising=False)
    with pytest.raises(ValueError):runtime.snapshot()
    assert not touches


@pytest.fixture
def controller(tmp_path,monkeypatch):
    source=Path(__file__).resolve().parents[1]/'experiments/staged_rts24_shadow_replay_v2.py'
    spec=importlib.util.spec_from_file_location('shadow_driver_under_test',source)
    d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
    root=tmp_path/'repo';root.mkdir();tables=root/'results/tables';tables.mkdir(parents=True)
    p1=tables/'p1';p1.mkdir();(p1/'fresh.json').write_text(json.dumps(dict(metrics={'outcome':'missing_input','coverage':False})))
    saved=p1/'data';saved.write_bytes(b'preserved')
    monkeypatch.setattr(d,'ROOT',root);monkeypatch.setattr(d,'P1',p1)
    monkeypatch.setattr(d,'BASE',tables/'shadow');monkeypatch.setattr(d,'OUTPUT',d.BASE/'shadow_01');monkeypatch.chdir(root)
    def input_check():d.require(saved.read_bytes()==b'preserved','P1 bytes differ')
    monkeypatch.setattr(d,'input_check',input_check)
    source_pin={'source':{'bytes':1,'sha256':'fixed'}}
    monkeypatch.setattr(d,'sources',lambda:source_pin)
    d._test_runtime=SimpleNamespace(unchanged=lambda before,refs:before)
    monkeypatch.setattr(d,'prepare',lambda:(d._test_runtime,None,None,{'legacy':'pins'},{'runtime':'pins'},{}))
    child='src/staged_rts24_child_optimality_v1.py'
    def supervise(argv,**kwargs):
        start=d.read(d.OUTPUT/'start.json')
        for name in ('worker.stdout.log','worker.stderr.log'):(d.OUTPUT/name).write_bytes(b'')
        d.event('complete')
        d.save(d.OUTPUT/'runtime_before.json',start['runtime']);d.save(d.OUTPUT/'runtime_after.json',start['runtime'])
        d.save(d.OUTPUT/'report.json',d.expected_report(start))
        d.save(d.OUTPUT/'shadow.json',dict(authority='DRAFT_NONAUTHORITATIVE',counts=d.EXPECTED,
            callers={str(root/child)+'|audit_child_lp|1':118,str(root/'other.py')+'|other|1':2429},
            pending=0,first_error=None,monitor_cleaned=True,
            scope='actual_legacy_JSON_bytes_and_digest_returns_not_CAS_blob_identity_or_speedup'))
        return dict(exit_code=0,stop_reason=None,job_quiet_confirmed=True)
    from src import staged_rts24_process_guard_v1 as guard
    monkeypatch.setattr(guard,'supervise',supervise)
    return d,guard,saved


def test_controller_adopts_only_postquiet_and_refuses_reuse(controller):
    d,_,_=controller
    assert d.launch()==0
    record=d.read(d.OUTPUT/'postquiet.json')
    assert record['P1_rechecked_after_quiet'] is True and len(record['output_pins'])==8
    with pytest.raises(FileExistsError):d.launch()


@pytest.mark.parametrize('fault',['P1_drift','source_drift','missing','extra','runtime','report_flag','count','caller','not_quiet','nonzero','parent_runtime'])
def test_controller_faults_are_not_success(controller,monkeypatch,fault):
    d,guard,saved=controller;original=guard.supervise
    def changed(*args,**kwargs):
        record=original(*args,**kwargs)
        if fault=='P1_drift':saved.write_bytes(b'changed after worker')
        elif fault=='source_drift':monkeypatch.setattr(d,'sources',lambda:{'different':'source'})
        elif fault=='missing':(d.OUTPUT/'shadow.json').unlink()
        elif fault=='extra':(d.OUTPUT/'extra').write_bytes(b'unknown')
        elif fault=='not_quiet':record['job_quiet_confirmed']=False
        elif fault=='nonzero':record['exit_code']=2
        elif fault=='parent_runtime':
            monkeypatch.setattr(d._test_runtime,'unchanged',lambda before,refs:{'changed_after_quiet':True})
        else:
            name='runtime_after.json' if fault=='runtime' else ('report.json' if fault=='report_flag' else 'shadow.json')
            path=d.OUTPUT/name;body=d.read(path)
            if fault=='runtime':body['different']=True
            elif fault=='report_flag':body['formal_result']=0
            elif fault=='count':body['counts']['digest_returned']=2546
            else:
                key=next(k for k in body['callers'] if 'audit_child_lp' in k);body['callers'][key]=117
            path.write_text(json.dumps(body))
        return record
    monkeypatch.setattr(guard,'supervise',changed)
    assert d.launch()==1
    assert not (d.OUTPUT/'postquiet.json').exists()
    assert d.read(d.OUTPUT/'adoption_failure.json')['accepted_success'] is False


def test_controller_reparse_output_is_refused(controller,monkeypatch):
    d,guard,_=controller;original=guard.supervise;old=Path.lstat
    def changed(*args,**kwargs):
        result=original(*args,**kwargs)
        target=d.OUTPUT/'report.json'
        def lstat(self,*a,**kw):
            info=old(self,*a,**kw)
            return SimpleNamespace(st_mode=info.st_mode,st_file_attributes=0x400) if self==target else info
        monkeypatch.setattr(Path,'lstat',lstat)
        return result
    monkeypatch.setattr(guard,'supervise',changed)
    assert d.launch()==1
    assert not (d.OUTPUT/'postquiet.json').exists()


@pytest.mark.parametrize('error',[ValueError,MemoryError,KeyboardInterrupt])
@pytest.mark.parametrize('fault',[None,'summary','write','preexisting'])
def test_worker_failure_saves_diagnostic_and_preserves_exception(controller,monkeypatch,error,fault):
    d,_,_=controller;d.create_output()
    identity={'runtime':'pins'};legacy_pins={'legacy':'pins'}
    start=dict(source_pins=d.sources(),runtime=identity,legacy_pins=legacy_pins)
    d.save(d.OUTPUT/'start.json',start)
    diagnostic=dict(counts={'digest_returned':3,'strict_unsupported':2},pending=0,monitor_cleaned=True,
        first_error=dict(reason='strict_unsupported',digest_ordinal=2,caller='fixed_caller',root_type='dict'))
    calls=[]
    class FailedMonitor:
        def __init__(self,*a,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*args):raise error('original monitor failure')
        def summary(self):
            if fault=='summary':raise OSError('secondary summary failure')
            return diagnostic
    fake=SimpleNamespace(routes=lambda:({},{}),shadow=SimpleNamespace(ShadowMonitor=FailedMonitor),
        journal=SimpleNamespace(reopen=lambda *a:calls.append('original_reopen')))
    monkeypatch.setattr(d,'prepare',lambda:(fake,None,None,legacy_pins,identity,{}))
    if fault=='preexisting':d.save(d.OUTPUT/'diagnostic.json',{'prior':'preserved'})
    elif fault=='write':
        save=d.save
        def failed(path,value):
            if path.name=='diagnostic.json':raise OSError('secondary storage failure')
            return save(path,value)
        monkeypatch.setattr(d,'save',failed)
    with pytest.raises(error,match='original monitor failure'):d.worker(d.stamp(d.OUTPUT/'start.json')['sha256'])
    assert calls==['original_reopen']
    if fault is None:assert d.read(d.OUTPUT/'diagnostic.json')==diagnostic
    elif fault=='preexisting':assert d.read(d.OUTPUT/'diagnostic.json')=={'prior':'preserved'}
    else:assert not (d.OUTPUT/'diagnostic.json').exists()
    assert not (d.OUTPUT/'report.json').exists() and not (d.OUTPUT/'runtime_after.json').exists()
